import math
import random
import json
import os
from datetime import datetime

GUESS = 0.25          # c: 1/4 chance of randomly guessing a 4-direction Tumbling-E
SLIP = 0.05           # s: 5% chance the user accidentally presses the wrong key
TARGET_PROB = 0.80    # tau: k1 is defined as the letter size with 80% accuracy
NUM_PARTICLES = 5000  # Number of particles for Likelihood Weighting

# Gumbel Prior Parameters for LogMAR = log10(k1) 
# Mode at 0.3 logMAR 
GUMBEL_MU = 0.30
GUMBEL_BETA = 0.38

# Standard ISO/IEC 7810 ID-1 Credit / Bank Card dimensions in millimeters
CARD_WIDTH_MM = 85.60
CARD_HEIGHT_MM = 53.98

# Local file used to persist user vision history over time
HISTORY_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vision_history.json")


# =====================================================================
# 1. BAYESIAN BELIEF INITIALIZATION & UPDATE 
# =====================================================================

def get_prior_belief(num_particles=NUM_PARTICLES, prior_mu=GUMBEL_MU, prior_beta=GUMBEL_BETA):
    """
    Algorithm 1, Step 1: Initialize belief of p(k1, k0) with 5,000 particles.
    Each particle is a dictionary: {'k1': ..., 'logmar': ..., 'k0': ..., 'weight': ...}
    """
    belief = []
    initial_weight = 1.0 / num_particles

    for _ in range(num_particles):
        # Sample logMAR from the Gumbel prior supported on [-0.55, 1.20] logMAR
        # At N=0 this gives MAP = 0.3 logMAR (2.0 arcmin) and 95% Interval [0.5, 12.6] arcmins
        logmar = sample_prior_logmar(prior_mu, prior_beta)
        k1 = 10.0 ** logmar

        # Sample k0 | k1: k0 is the size where vision starts (must satisfy 0 < k0 < k1)
        k0 = random.uniform(0.50 * k1, 0.90 * k1)

        belief.append({
            'k1': k1,
            'logmar': logmar,
            'k0': k0,
            'weight': initial_weight
        })

    return belief


def update_belief(prior, observation):
    """
    Algorithm 1, Step 2(iii): Come up with a new belief after seeing an observation.
    observation is a dict: {'size': font_size_in_arcmins, 'correct': True/False}
    """
    for particle in prior:
        p_obs = p_observation_given_acuity(particle, observation)
        particle['weight'] *= p_obs

    normalize(prior)
    return prior


def p_observation_given_acuity(particle, observation):
    """
    Calculates p(d_i | k0, k1): how likely it is that a patient with this
    particle's (k0, k1) gets `observation['size']` correct or incorrect.
    """
    font_size = observation['size']
    p_correct = p_correct_given_acuity(particle['k0'], particle['k1'], font_size)

    if observation['correct']:
        return p_correct
    else:
        return 1.0 - p_correct


def p_correct_given_acuity(k0, k1, font_size):
    """
    Section 2 & 3: Combines the Floored Exponential Visual Response Function
    with the human 'slip' probability:
        v_s(x) = s * c + (1 - s) * v(x, k0, k1)
    """
    p_no_slip = floored_exponential(font_size, k0, k1)
    return SLIP * GUESS + (1.0 - SLIP) * p_no_slip


def floored_exponential(x, k0, k1):
    """
    Appendix B: The Floored Exponential Visual Response Function v(x, k0, k1).
    - For x <= k0: the patient cannot discern the letter and guesses with prob `c`.
    - For x > k0: accuracy rises exponentially, passing through (k1, TARGET_PROB).
    """
    if x <= k0:
        return GUESS

    base = (1.0 - TARGET_PROB) / (1.0 - GUESS)
    exponent = (x - k0) / (k1 - k0)

    if exponent > 100.0:
        return 1.0

    return 1.0 - (1.0 - GUESS) * (base ** exponent)


def choose_next_letter_size(belief):
    """
    Algorithm 1, Step 2(i): Posterior Probability Matching (Thompson Sampling).
    Randomly picks a particle with probability equal to its weight and returns its k1.
    """
    r = random.random()
    cumulative = 0.0
    for particle in belief:
        cumulative += particle['weight']
        if r <= cumulative:
            return particle['k1']
    return belief[-1]['k1']


def normalize(belief):
    """
    Makes sure all particle weights sum to 1.0.
    """
    total = sum(p['weight'] for p in belief)
    if total <= 0.0:
        uniform_w = 1.0 / len(belief)
        for p in belief:
            p['weight'] = uniform_w
    else:
        for p in belief:
            p['weight'] /= total


# =====================================================================
# 2. PREDICTIONS, CONFIDENCE & BOTH POSTERIOR CURVES (ARCMINS + LOGMAR)
# =====================================================================

def get_predicted_acuity(belief):
    """
    Returns the expected value (posterior mean) of visual acuity k1 in arcminutes.
    """
    return sum(p['k1'] * p['weight'] for p in belief)


def get_map_acuity_logmar(belief):
    """
    Returns the MAP estimate in LogMAR (and corresponding arcmins = 10^logMAR)
    from the smoothed LogMAR posterior curve, matching myeyes.ai/measure.
    """
    xs_logmar, ys_logmar = get_smooth_posterior_curve_logmar(belief)
    best_idx = max(range(len(ys_logmar)), key=lambda i: ys_logmar[i])
    best_logmar = xs_logmar[best_idx]
    best_arcmin = 10.0 ** best_logmar
    return best_arcmin, best_logmar


def get_map_acuity(belief):
    """
    Algorithm 1, Step 3: Returns argmax_k1 p(k1 | D) in arcminutes.
    """
    best_arcmin, _ = get_map_acuity_logmar(belief)
    return best_arcmin


def get_confidence_within_10_percent(belief):
    """
    Section 5 (StAT-star & Calibrated Uncertainty):
    Computes the probability that the true acuity k1 is within +/-10% (relative error < 0.10)
    of our current predicted acuity.
    """
    predicted_k1 = get_predicted_acuity(belief)
    if predicted_k1 <= 0:
        return 0.0

    confidence = 0.0
    for p in belief:
        relative_error = abs(p['k1'] - predicted_k1) / predicted_k1
        if relative_error < 0.10:
            confidence += p['weight']
    return confidence


def get_credible_interval(belief, credibility=0.95):
    """
    Returns the (low, high) interval of k1 in arcmins containing `credibility` (95%)
    of the posterior weight (e.g., [0.5, 12.6] arcmins at N done = 0).
    """
    sorted_particles = sorted(belief, key=lambda p: p['k1'])
    tail = (1.0 - credibility) / 2.0

    cum = 0.0
    low_k1 = sorted_particles[0]['k1']
    high_k1 = sorted_particles[-1]['k1']

    found_low = False
    for p in sorted_particles:
        cum += p['weight']
        if not found_low and cum >= tail:
            low_k1 = p['k1']
            found_low = True
        if cum >= 1.0 - tail:
            high_k1 = p['k1']
            break

    return low_k1, high_k1


def _compute_adaptive_logmar_kde(belief, min_logmar=-0.8, max_logmar=1.25, num_points=100):
    """
    Internal helper: computes the posterior likelihood distribution over LogMAR
    using Adaptive Gaussian KDE.
    """
    ws = [p['weight'] for p in belief]
    logmars = [math.log10(max(1e-6, p['k1'])) for p in belief]
    mean_log = sum(l * w for l, w in zip(logmars, ws))
    std_log = math.sqrt(max(1e-6, sum(w * ((l - mean_log) ** 2) for l, w in zip(logmars, ws))))

    bandwidth = max(0.030, min(0.095, 0.265 * std_log))

    bin_width = (max_logmar - min_logmar) / num_points
    bin_centers = [min_logmar + (i + 0.5) * bin_width for i in range(num_points)]
    bin_weights = [0.0] * num_points

    for p in belief:
        lg = math.log10(max(1e-6, p['k1']))
        idx = int((lg - min_logmar) / bin_width)
        if 0 <= idx < num_points:
            bin_weights[idx] += p['weight']

    inv_2sigma2 = 1.0 / (2.0 * bandwidth * bandwidth)
    raw_ys = []
    for x in bin_centers:
        val = 0.0
        for b_x, b_w in zip(bin_centers, bin_weights):
            if b_w > 0:
                diff = x - b_x
                val += b_w * math.exp(-(diff * diff) * inv_2sigma2)
        raw_ys.append(val)

    total_raw = sum(raw_ys) or 1.0
    clinical_steps = 22.5
    scale = (num_points / clinical_steps) / total_raw
    ys = [min(1.0, v * scale) for v in raw_ys]
    return bin_centers, ys, bandwidth, bin_weights, scale


def get_smooth_posterior_curve_logmar(belief, min_logmar=-0.8, max_logmar=1.25, num_points=100, bandwidth=None):
    """
    CHART 2 (Bottom Chart): Smooth 1D posterior likelihood curve over Acuity in LogMAR [-0.8 .. 1.2].
    """
    bin_centers, ys, _, _, _ = _compute_adaptive_logmar_kde(
        belief, min_logmar=min_logmar, max_logmar=max_logmar, num_points=num_points
    )
    return bin_centers, ys


def get_smooth_posterior_curve_arcmins(belief, max_x=12.0, num_points=120, bandwidth=None):
    """
    CHART 1 (Top Chart): Smooth 1D posterior likelihood curve over Acuity in ARCMINS [0 .. 12].
    """
    log_centers, _, bw_log, bin_weights, scale = _compute_adaptive_logmar_kde(belief)
    inv_2sigma2 = 1.0 / (2.0 * bw_log * bw_log)

    step_x = max_x / num_points
    arc_xs = [(i + 0.5) * step_x for i in range(num_points)]
    arc_ys = []

    for x in arc_xs:
        if x < 0.20:
            arc_ys.append(0.0)
            continue
        lg_x = math.log10(x)
        val = 0.0
        for b_x, b_w in zip(log_centers, bin_weights):
            if b_w > 0:
                diff = lg_x - b_x
                val += b_w * math.exp(-(diff * diff) * inv_2sigma2)
        arc_ys.append(min(1.0, val * scale))

    return arc_xs, arc_ys


def get_smooth_posterior_curve(belief, max_x=12.0, num_points=120, bandwidth=None):
    return get_smooth_posterior_curve_arcmins(belief, max_x=max_x, num_points=num_points, bandwidth=bandwidth)


def get_nice_y_axis_ticks(max_y_val):
    """
    Computes clean, human-readable Y-axis (Likelihood) ticks and axis ceiling.
    """
    if max_y_val <= 0.10:
        step = 0.025
    elif max_y_val <= 0.20:
        step = 0.05
    elif max_y_val <= 0.40:
        step = 0.10
    elif max_y_val <= 0.60:
        step = 0.15
    elif max_y_val <= 0.80:
        step = 0.20
    else:
        step = 0.25

    top_tick = 4.0 * step
    axis_ceiling = max(top_tick * 1.03, max_y_val * 1.05)

    ticks = []
    for i in range(5):
        tv = round(i * step, 4)
        if i == 0:
            lbl = "0"
        elif abs(tv * 10 - round(tv * 10)) < 1e-6:
            lbl = f"{tv:.1f}"
        else:
            s = f"{tv:.3f}".rstrip("0")
            if s.startswith("0."):
                s = s[1:]
            lbl = s
        ticks.append((tv, lbl))

    return axis_ceiling, ticks


# =====================================================================
# 3. CLINICAL & OPTICAL CONVERSIONS + 0 TO 100 (100+) SCORE
# =====================================================================

def arcmins_to_score_0_100(arcmins):
    """
    Converts visual acuity in arcminutes into an intuitive 0 to 100 Vision Score:
    - 1.0 arcmin (20/20 normal vision) -> 100
    - Better than 20/20 (arcmins < 0.995, raw score > 100) -> "100+"
    - 2.0 arcmins (20/40) -> "50"
    - 10.0 arcmins (20/200) -> "10"

    Returns a tuple: (formatted_string, numeric_value_capped_at_105)
    """
    arcmins = max(0.05, float(arcmins))
    raw_score = round(100.0 / arcmins)
    if raw_score > 100:
        return "100+", 105
    clamped = max(0, min(100, int(raw_score)))
    return str(clamped), clamped


def arcmins_interval_to_score_0_100(ci_low_arcmin, ci_high_arcmin):
    """
    Converts a 95% confidence interval [ci_low_arcmin, ci_high_arcmin] into
    the 0 to 100 (100+) score interval.
    Note: Smaller arcmins = sharper vision = higher 0-100 score.
    """
    low_score_str, _ = arcmins_to_score_0_100(ci_high_arcmin)
    high_score_str, _ = arcmins_to_score_0_100(ci_low_arcmin)
    return f"{low_score_str} to {high_score_str}"


def calculate_screen_pixels_per_mm(screen_width_px, screen_height_px, diagonal_inches=15.6):
    """
    Calculates exact `pixels_per_mm` and exact Credit Card width in pixels
    for a laptop/monitor of `diagonal_inches` (default: 15.6 inches).
    """
    diagonal_mm = diagonal_inches * 25.4
    aspect = float(screen_width_px) / max(1.0, float(screen_height_px))
    screen_width_mm = diagonal_mm * (aspect / math.sqrt(aspect * aspect + 1.0))
    pixels_per_mm = float(screen_width_px) / screen_width_mm
    card_width_px = CARD_WIDTH_MM * pixels_per_mm
    return pixels_per_mm, card_width_px


def arcmins_to_letter_height_mm(arcmins, distance_cm):
    """
    Appendix A (Units of Acuity):
    Converts a visual acuity stroke angle `x` (in arcminutes) into the physical
    height (in millimeters) of a standard 5x5 Tumbling-E optotype at `distance_cm`.
    """
    distance_mm = distance_cm * 10.0
    total_angle_degrees = (5.0 * arcmins) / 60.0
    half_angle_radians = math.radians(total_angle_degrees / 2.0)
    height_mm = 2.0 * distance_mm * math.tan(half_angle_radians)
    return height_mm


def arcmins_to_pixels(arcmins, distance_cm, pixels_per_mm):
    """
    Converts optotype size from arcminutes directly to screen pixels using
    the user's calibrated `pixels_per_mm` and viewing `distance_cm`.
    """
    height_mm = arcmins_to_letter_height_mm(arcmins, distance_cm)
    return height_mm * pixels_per_mm


def arcmins_to_clinical_metrics(arcmins):
    """
    Converts MAR (Minimum Angle of Resolution in arcminutes) into:
    - Score 0-100 ("100+" if better than 100, else "0".."100")
    - Snellen Feet (20 / X)
    - Snellen Meters (6 / X)
    - LogMAR (log10 of arcmins)
    - Decimal acuity (1 / arcmins)
    """
    arcmins = max(0.1, arcmins)
    snellen_ft_denom = round(20.0 * arcmins)
    snellen_m_denom = round(6.0 * arcmins, 1)
    logmar = math.log10(arcmins)
    decimal_acuity = 1.0 / arcmins
    score_str, score_num = arcmins_to_score_0_100(arcmins)

    return {
        'arcmins': arcmins,
        'score_0_100': score_str,
        'score_0_100_num': score_num,
        'snellen_feet': f"20/{snellen_ft_denom}",
        'snellen_meters': f"6/{snellen_m_denom}",
        'logmar': logmar,
        'decimal': decimal_acuity
    }


def sample_prior_logmar(mu=GUMBEL_MU, beta=GUMBEL_BETA):
    """
    Samples logMAR = log10(k1) from a Gumbel distribution centered at `mu = 0.3` logMAR
    (mode = 2.0 arcmins) and supported on [-0.55, 1.20] logMAR.
    """
    while True:
        u = random.uniform(1e-12, 1.0 - 1e-12)
        if random.random() < 0.55:
            val = mu + beta * math.log(-math.log(u))
        else:
            val = mu - beta * math.log(-math.log(u))
        if -0.55 <= val <= 1.20:
            return val


# =====================================================================
# 4. VISION HISTORY TRACKING OVER TIME (PERSISTENT LOCAL LOG)
# =====================================================================

def load_vision_history(filepath=HISTORY_FILE_PATH):
    """
    Loads the list of past vision test records from `vision_history.json`.
    """
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def append_vision_history_record(record, filepath=HISTORY_FILE_PATH):
    """
    Appends a completed eye test record (with user_name, test_date, eye,
    score_0_100, map_k1, map_logmar, snellen_feet, ci_low, ci_high) to `vision_history.json`.
    """
    history = load_vision_history(filepath)
    history.append(record)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return history


def clear_vision_history(filepath=HISTORY_FILE_PATH):
    """
    Clears all saved vision history records.
    """
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception:
        pass
    return []

