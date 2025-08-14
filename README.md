# 💊 AI_Prescription_Verifier

> *Upload a doctor's prescription → Get instant, clear insights on drug safety, interactions, age-appropriate dosing, and brand alternatives.*

This project is a *Streamlit-based AI application* with an *animated, premium UI* that helps verify prescriptions using OCR, NLP, and medical datasets (RxNorm, Drug–Drug Interactions). It’s designed for educational support — *not a medical device*.

---

## ✨ Features

- *Upload & Extract*  
  Upload prescription images or PDFs → OCR + NLP extract drugs, doses, routes, frequencies.
  
- *Drug Mapping*  
  Map drugs to *RxNorm RxCUIs* via the *RxNav REST API*.

- *Interaction Checks*  
  Cross-check against a curated Drug–Drug Interaction dataset.

- *Severity Classification*  
  AI classifier + rule-based boosts to detect *low/medium/high severity*.

- *Age-based Dosage Verification*  
  Pediatric (<12) & Geriatric (≥65) safe dose suggestions.

- *Brand Alternatives*  
  Suggest safer or brand-name equivalents.

- *Layman Summaries*  
  Summarized advice using *BART* transformer.

- *Beautiful UI*  
  - Gradient headers, glassmorphism cards, micro-interactions  
  - *Lottie animations*, progress steppers, confetti for safe results

- *Exports*  
  Save results as *CSV* or *PDF* reports.
