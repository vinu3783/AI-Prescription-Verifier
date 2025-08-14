import os
import json
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
from dataclasses import dataclass, asdict
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReminderType(Enum):
    MEDICATION = "medication"
    WATER = "water"
    MEAL = "meal"
    EXERCISE = "exercise"

class ReminderStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    MISSED = "missed"
    SNOOZED = "snoozed"

@dataclass
class MedicationReminder:
    """Medication reminder data structure"""
    id: str
    drug_name: str
    dosage: str
    frequency: str  # 'once_daily', 'twice_daily', 'three_times_daily', 'four_times_daily', 'as_needed'
    times: List[str]  # List of times like ['08:00', '20:00']
    instructions: str  # 'with food', 'before meal', 'at bedtime', etc.
    start_date: str
    end_date: Optional[str] = None
    created_at: str = None
    last_taken: Optional[str] = None
    streak_days: int = 0
    total_doses_taken: int = 0
    total_doses_prescribed: int = 0
    is_active: bool = True

@dataclass
class WaterReminder:
    """Water intake reminder data structure"""
    id: str
    target_glasses: int = 8  # Default 8 glasses per day
    glass_size_ml: int = 250  # Default 250ml per glass
    interval_minutes: int = 120  # Every 2 hours
    start_time: str = "07:00"
    end_time: str = "22:00"
    is_active: bool = True
    current_intake: int = 0  # Glasses consumed today
    last_reminder: Optional[str] = None

class SmartReminderSystem:
    """
    Comprehensive reminder system for medications and water intake
    """
    
    def __init__(self):
        self.data_dir = Path("data/reminders")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.med_reminders_file = self.data_dir / "medication_reminders.json"
        self.water_reminders_file = self.data_dir / "water_reminders.json"
        self.reminder_log_file = self.data_dir / "reminder_log.json"
        
        self.medication_reminders: Dict[str, MedicationReminder] = {}
        self.water_reminders: Dict[str, WaterReminder] = {}
        self.reminder_log: List[Dict] = []
        
        self.load_data()

    def load_data(self):
        """Load reminders from storage"""
        try:
            # Load medication reminders
            if self.med_reminders_file.exists():
                with open(self.med_reminders_file, 'r') as f:
                    data = json.load(f)
                    self.medication_reminders = {
                        k: MedicationReminder(**v) for k, v in data.items()
                    }
            
            # Load water reminders
            if self.water_reminders_file.exists():
                with open(self.water_reminders_file, 'r') as f:
                    data = json.load(f)
                    self.water_reminders = {
                        k: WaterReminder(**v) for k, v in data.items()
                    }
            
            # Load reminder log
            if self.reminder_log_file.exists():
                with open(self.reminder_log_file, 'r') as f:
                    self.reminder_log = json.load(f)
            
            logger.info("✅ Reminder data loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading reminder data: {e}")

    def save_data(self):
        """Save reminders to storage"""
        try:
            # Save medication reminders
            med_data = {k: asdict(v) for k, v in self.medication_reminders.items()}
            with open(self.med_reminders_file, 'w') as f:
                json.dump(med_data, f, indent=2)
            
            # Save water reminders  
            water_data = {k: asdict(v) for k, v in self.water_reminders.items()}
            with open(self.water_reminders_file, 'w') as f:
                json.dump(water_data, f, indent=2)
            
            # Save reminder log (keep last 1000 entries)
            if len(self.reminder_log) > 1000:
                self.reminder_log = self.reminder_log[-1000:]
            
            with open(self.reminder_log_file, 'w') as f:
                json.dump(self.reminder_log, f, indent=2)
            
            logger.info("✅ Reminder data saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving reminder data: {e}")

    def create_medication_reminder_from_prescription(self, entities: List[Dict]) -> List[MedicationReminder]:
        """
        Create medication reminders from prescription analysis
        
        Args:
            entities: List of drug entities from NER analysis
            
        Returns:
            List of created medication reminders
        """
        created_reminders = []
        
        for entity in entities:
            drug_name = entity.get('drug', '')
            dosage = entity.get('dose', '')
            frequency = entity.get('frequency', '')
            
            if not drug_name:
                continue
            
            # Parse frequency and create reminder times
            times = self.parse_frequency_to_times(frequency)
            if not times:
                times = ['08:00']  # Default morning dose
            
            # Create reminder
            reminder_id = f"med_{len(self.medication_reminders) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            reminder = MedicationReminder(
                id=reminder_id,
                drug_name=drug_name,
                dosage=dosage,
                frequency=frequency,
                times=times,
                instructions=self.get_medication_instructions(drug_name),
                start_date=datetime.now().strftime('%Y-%m-%d'),
                created_at=datetime.now().isoformat()
            )
            
            self.medication_reminders[reminder_id] = reminder
            created_reminders.append(reminder)
            
            logger.info(f"Created reminder for {drug_name}")
        
        self.save_data()
        return created_reminders

    def parse_frequency_to_times(self, frequency: str) -> List[str]:
        """Convert frequency string to reminder times"""
        if not frequency:
            return ['08:00']
        
        freq_lower = frequency.lower()
        
        # Common frequency mappings
        if 'once' in freq_lower or 'daily' in freq_lower and 'twice' not in freq_lower:
            return ['08:00']
        elif 'twice' in freq_lower or 'bid' in freq_lower:
            return ['08:00', '20:00']
        elif 'three times' in freq_lower or 'tid' in freq_lower:
            return ['08:00', '14:00', '20:00']
        elif 'four times' in freq_lower or 'qid' in freq_lower:
            return ['08:00', '12:00', '16:00', '20:00']
        elif 'every 4 hours' in freq_lower or 'q4h' in freq_lower:
            return ['06:00', '10:00', '14:00', '18:00', '22:00']
        elif 'every 6 hours' in freq_lower or 'q6h' in freq_lower:
            return ['06:00', '12:00', '18:00', '24:00']
        elif 'every 8 hours' in freq_lower or 'q8h' in freq_lower:
            return ['08:00', '16:00', '24:00']
        elif 'bedtime' in freq_lower or 'night' in freq_lower:
            return ['22:00']
        elif 'morning' in freq_lower:
            return ['08:00']
        else:
            return ['08:00']  # Default

    def get_medication_instructions(self, drug_name: str) -> str:
        """Get specific instructions for common medications"""
        drug_lower = drug_name.lower()
        
        # Common medication instructions
        instructions_map = {
            'aspirin': 'Take with food to prevent stomach upset',
            'ibuprofen': 'Take with food or milk',
            'paracetamol': 'Can be taken with or without food',
            'acetaminophen': 'Can be taken with or without food',
            'metformin': 'Take with meals to reduce stomach upset',
            'lisinopril': 'Take at the same time each day',
            'atorvastatin': 'Take at bedtime for best effect',
            'simvastatin': 'Take in the evening with dinner',
            'warfarin': 'Take at the same time daily, avoid alcohol',
            'digoxin': 'Take on empty stomach, check pulse',
            'furosemide': 'Take in morning to avoid nighttime urination',
            'amlodipine': 'Take at the same time each day'
        }
        
        # Find matching instruction
        for drug, instruction in instructions_map.items():
            if drug in drug_lower:
                return instruction
        
        return 'Take as prescribed by your doctor'

    def create_water_reminder(self, target_glasses: int = 8, interval_minutes: int = 120) -> WaterReminder:
        """Create a water intake reminder"""
        
        reminder_id = f"water_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        reminder = WaterReminder(
            id=reminder_id,
            target_glasses=target_glasses,
            interval_minutes=interval_minutes
        )
        
        self.water_reminders[reminder_id] = reminder
        self.save_data()
        
        logger.info(f"Created water reminder: {target_glasses} glasses every {interval_minutes} minutes")
        return reminder

    def get_current_reminders(self) -> Dict[str, List]:
        """Get current due reminders"""
        current_time = datetime.now()
        current_date = current_time.strftime('%Y-%m-%d')
        current_time_str = current_time.strftime('%H:%M')
        
        due_medications = []
        due_water = []
        
        # Check medication reminders
        for reminder in self.medication_reminders.values():
            if not reminder.is_active:
                continue
            
            for time_str in reminder.times:
                # Check if this time is due (within 30 minutes)
                reminder_time = datetime.strptime(f"{current_date} {time_str}", '%Y-%m-%d %H:%M')
                time_diff = (current_time - reminder_time).total_seconds() / 60
                
                if -30 <= time_diff <= 30:  # Due within 30 minutes
                    due_medications.append({
                        'reminder': reminder,
                        'due_time': time_str,
                        'status': 'due' if time_diff >= 0 else 'upcoming'
                    })
        
        # Check water reminders
        for reminder in self.water_reminders.values():
            if not reminder.is_active:
                continue
            
            if reminder.last_reminder:
                last_reminder_time = datetime.fromisoformat(reminder.last_reminder)
                minutes_since_last = (current_time - last_reminder_time).total_seconds() / 60
                
                if minutes_since_last >= reminder.interval_minutes:
                    due_water.append(reminder)
            else:
                # First reminder of the day
                due_water.append(reminder)
        
        return {
            'medications': due_medications,
            'water': due_water
        }

    def mark_medication_taken(self, reminder_id: str, taken_time: Optional[str] = None) -> bool:
        """Mark a medication as taken"""
        if reminder_id not in self.medication_reminders:
            return False
        
        reminder = self.medication_reminders[reminder_id]
        taken_time = taken_time or datetime.now().isoformat()
        
        # Update reminder
        reminder.last_taken = taken_time
        reminder.total_doses_taken += 1
        
        # Update streak
        today = datetime.now().date()
        if reminder.last_taken:
            last_taken_date = datetime.fromisoformat(reminder.last_taken).date()
            if last_taken_date == today:
                reminder.streak_days += 1
            elif last_taken_date != today - timedelta(days=1):
                reminder.streak_days = 1  # Reset streak
        else:
            reminder.streak_days = 1
        
        # Log the action
        self.log_reminder_action(reminder_id, ReminderType.MEDICATION, ReminderStatus.COMPLETED, taken_time)
        
        self.save_data()
        return True

    def mark_water_consumed(self, reminder_id: str, glasses: int = 1) -> bool:
        """Mark water consumption"""
        if reminder_id not in self.water_reminders:
            return False
        
        reminder = self.water_reminders[reminder_id]
        reminder.current_intake += glasses
        reminder.last_reminder = datetime.now().isoformat()
        
        # Log the action
        self.log_reminder_action(reminder_id, ReminderType.WATER, ReminderStatus.COMPLETED)
        
        self.save_data()
        return True

    def log_reminder_action(self, reminder_id: str, reminder_type: ReminderType, status: ReminderStatus, timestamp: str = None):
        """Log reminder actions for analytics"""
        log_entry = {
            'reminder_id': reminder_id,
            'type': reminder_type.value,
            'status': status.value,
            'timestamp': timestamp or datetime.now().isoformat()
        }
        
        self.reminder_log.append(log_entry)

    def get_adherence_stats(self, days: int = 7) -> Dict:
        """Get medication adherence statistics"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stats = {
            'total_medications': len(self.medication_reminders),
            'active_medications': len([r for r in self.medication_reminders.values() if r.is_active]),
            'adherence_rate': 0.0,
            'streak_days': 0,
            'total_doses_taken': 0,
            'total_doses_prescribed': 0,
            'water_goal_achievement': 0.0
        }
        
        # Calculate medication adherence
        total_taken = sum(r.total_doses_taken for r in self.medication_reminders.values())
        total_prescribed = sum(r.total_doses_prescribed for r in self.medication_reminders.values())
        
        if total_prescribed > 0:
            stats['adherence_rate'] = (total_taken / total_prescribed) * 100
        
        stats['total_doses_taken'] = total_taken
        stats['total_doses_prescribed'] = total_prescribed
        
        # Calculate average streak
        active_reminders = [r for r in self.medication_reminders.values() if r.is_active]
        if active_reminders:
            stats['streak_days'] = sum(r.streak_days for r in active_reminders) / len(active_reminders)
        
        return stats

    def get_reminder_notifications(self) -> List[Dict]:
        """Get formatted reminder notifications for UI"""
        current_reminders = self.get_current_reminders()
        notifications = []
        
        # Medication notifications
        for med_reminder in current_reminders['medications']:
            reminder = med_reminder['reminder']
            status = med_reminder['status']
            due_time = med_reminder['due_time']
            
            icon = "💊"
            if status == 'upcoming':
                icon = "⏰"
            
            notifications.append({
                'id': reminder.id,
                'type': 'medication',
                'icon': icon,
                'title': f"{reminder.drug_name} - {reminder.dosage}",
                'message': f"Due at {due_time}. {reminder.instructions}",
                'priority': 'high' if status == 'due' else 'medium',
                'action_required': True
            })
        
        # Water notifications
        for water_reminder in current_reminders['water']:
            remaining = water_reminder.target_glasses - water_reminder.current_intake
            
            notifications.append({
                'id': water_reminder.id,
                'type': 'water',
                'icon': "💧",
                'title': "Time to hydrate!",
                'message': f"Drink a glass of water. {remaining} glasses remaining today.",
                'priority': 'medium',
                'action_required': True
            })
        
        return notifications

    def snooze_reminder(self, reminder_id: str, minutes: int = 10) -> bool:
        """Snooze a reminder for specified minutes"""
        # This would be implemented with a proper scheduling system
        # For now, just log the snooze action
        self.log_reminder_action(reminder_id, ReminderType.MEDICATION, ReminderStatus.SNOOZED)
        return True

    def get_weekly_report(self) -> Dict:
        """Generate weekly adherence report"""
        stats = self.get_adherence_stats(7)
        
        report = {
            'week_ending': datetime.now().strftime('%Y-%m-%d'),
            'adherence_rate': stats['adherence_rate'],
            'doses_taken': stats['total_doses_taken'],
            'current_streak': stats['streak_days'],
            'active_medications': stats['active_medications'],
            'recommendations': []
        }
        
        # Add recommendations based on adherence
        if stats['adherence_rate'] < 80:
            report['recommendations'].append("Consider setting more frequent reminders")
            report['recommendations'].append("Discuss adherence challenges with your doctor")
        elif stats['adherence_rate'] >= 95:
            report['recommendations'].append("Excellent adherence! Keep up the great work!")
        
        if stats['streak_days'] < 3:
            report['recommendations'].append("Focus on building a consistent routine")
        
        return report

# Convenience functions
def create_reminders_from_prescription(entities: List[Dict]) -> List[MedicationReminder]:
    """Create medication reminders from prescription entities"""
    system = SmartReminderSystem()
    return system.create_medication_reminder_from_prescription(entities)

def get_current_notifications() -> List[Dict]:
    """Get current reminder notifications"""
    system = SmartReminderSystem()
    return system.get_reminder_notifications()

def mark_dose_taken(reminder_id: str) -> bool:
    """Mark a medication dose as taken"""
    system = SmartReminderSystem()
    return system.mark_medication_taken(reminder_id)

def mark_water_drunk(reminder_id: str, glasses: int = 1) -> bool:
    """Mark water consumption"""
    system = SmartReminderSystem()
    return system.mark_water_consumed(reminder_id, glasses)