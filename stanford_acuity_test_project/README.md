# Stanford Acuity Test (StAT) — Open-Source Rebuild
## Based on the AAAI-20 Paper by Piech, Malik, Scott, Chang & Lin (Stanford University)

This repository contains an open-source, offline-capable rebuild of the visual acuity test found at `https://myeyes.ai/measure`, implemented as part of my university Bachelor's Project. It includes the exact mathematical models from the original research paper, paired with a modern web and desktop GUI.

---

### 🌟 What We Built: Core Paper Implementation
- **Floored Exponential VRF**: Uses the paper's exact Visual Response Function (with a guessing floor of $c = 0.25$ and slip probability of $s = 0.05$).
- **Bayesian Particle Filter**: Uses Likelihood Weighting with 5,000 particles and the paper's LogMAR Gumbel Prior to dynamically update visual acuity belief.
- **Thompson Sampling**: Selects the next letter size using Posterior Probability Matching.
- **Dual Posterior Charts**: Live visualization of the probability density curves for both `arcmins` and `logMAR` (Kernel Density Estimation).
- **Calibrated Uncertainty**: Calculates the exact probability that the true acuity is within 10% of the prediction.

### 🚀 What's NEW (Our Custom Additions & Improvements)
We expanded upon the original paper and base website by adding several robust new features:

1. **Intuitive 0 to 100 Vision Score System (`100+`):**
   - Converts the scientific Minimum Angle of Resolution ($k_1$ in arcminutes) into a consumer-friendly **0 to 100 Vision Score** (`score = round(100 / arcmins)`). 
   - Standard 20/20 vision ($1.0\text{ arcmin}$) perfectly equals **`100`**. Any vision sharper than 20/20 displays as **`100+`**.
2. **Persistent Vision History Over Time (`vision_history.json`):**
   - Added user profiles (Name & Date) to track eye health longitudinally.
   - Includes a live **Interactive Trend Chart** that plots Left vs. Right eye scores across multiple dates on a single timeline.
3. **Advanced Export & Reporting Capabilities:**
   - **Visual Reports:** Exports a self-contained HTML/PNG report containing the side-by-side eye cards, 95% intervals, and embedded SVG posterior distribution curves.
   - **Raw Data Export:** One-click export of exam history to CSV (for Excel) and JSON.
4. **Adaptive "Continue or Finish" Modal:**
   - Instead of a hard stop at 20 questions, the UI halts and displays current MAP Acuity and Calibrated Confidence. The user can then strategically choose to add +10 or +20 questions to push for higher Bayesian certainty.
5. **High-DPI Vector Optotypes (Anti-Blur):**
   - Implemented a pure Vector SVG Tumbling-E with `shape-rendering="crispEdges"` and Windows DPI awareness, guaranteeing zero pixel-blur even on 15.6" laptops with 150% display scaling.
6. **Binocular Side-by-Side Results:**
   - Unified dashboard allowing seamless switching between testing the Left Eye and Right Eye, displaying both final result cards and distributions side-by-side.
7. **Auto-Calibration for Laptops:**
   - Automatically calculates exact physical pixel density based on the device's diagonal aspect ratio to size the credit card reference perfectly upon load.

---

### 💻 How to Run on Your Computer

1. **Run the Local Web Application (Recommended — opens in browser):**
```bash
python app_web.py
```

2. **Run the Desktop GUI Application (Tkinter):**
```bash
python app_desktop.py
```
---

## ⚖️ Attribution & Disclaimer

**Academic Project:** This repository contains an independent, open-source implementation created for a university bachelor project. 

**Algorithm:** The core algorithm (StAT) implemented in this code is based entirely on the research paper:
> Piech, C., Malik, A., Scott, L. M., Chang, R. T., & Lin, C. (2020). *"The Stanford Acuity Test: A Precise Vision Test Using Bayesian Techniques and a Discovery in Human Visual Response."* Proceedings of the AAAI Conference on Artificial Intelligence (AAAI-20).

**UI / UX:** The web interface and interactive design are an educational replica of the interface found at [myeyes.ai/measure](https://myeyes.ai/measure). 

**Disclaimer:** This software is for educational and research purposes only. It is NOT an official product of Stanford University or myeyes.ai. It is not an FDA-approved medical device and should not be used for actual medical diagnosis.

**License:** MIT License.
