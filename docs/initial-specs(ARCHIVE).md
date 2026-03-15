# Command Line Calibration Training - Initial App Specs

## Outline
A simple CLI app for improving your probabilistic calibration skills. The user runs the command, starting the program. There is a Claude Code style dashborad/title showing the user's calibration scores, questions answered, etc. The user can choose to start a new calibration session (/train), view past performance (including a calibration graph) (/stats), or adjust settings (/settings).

After choosing to start a calibration session, the user is prompted to choose between binary questions or confidence intervals. After that, they choose which specific questions to train (all available, previously wrong, specific categroies; the default is all available). In confidence interval mode, the user is prompted to choose a confidence level (eg. 50%, 60%, 70%, etc.) to train. In a confidence interval calibration session, the user is presented with a question and prompted to give their __% (based on what they chose earlier) confidence interval. For example, "when did the dinosaurs go extinct?" → Lower bound of 80 MYA, upper bound of 20 MYA. The units are automatically displayed, and the user can click back and forth between the lower and upper bound fields to edit their responses as many times as they want. In binary question mode, the user is presented with a question like "there are more than 8 billion people as of Jan. 1, 2026" and the user enters a probability estimate for whether it is true, eg. 75%. After they finish and click enter, the program asks them to confirm they're ready to submit their estimate(s), with the option to go back and edit. If they choose to submit, the program shows whether they were right or wrong and how many points they gained or lost for the question based on the scoring algorithm detailed below. The user hits enter to continue onto the next question. 

The user can hit Ctrl-C at any point to quit the calibration training session, at which point statistics for the session are shown. If the user hits Ctrl-C or types /exit at the title page, the program quits.

The program should store user data locally to track progress over time, both on overall calibration and to track completed questions.

## Scoring Algorithm

GREENBERG SCORING RULE FOR CALIBRATION INTERVALS

INPUTS:
- lowerBound: lower bound of confidence interval
- upperBound: upper bound of confidence interval
- answer: true value
- confidenceInterval: target confidence level (e.g., 80 for 80%)
- useLogScoring: boolean (true for multiplicative/log scale, false for linear)
- C: scale parameter (controls sensitivity)

CONSTANTS:
- SMAX = 10 (maximum score)
- SMIN = -57.2689368388 (minimum score/penalty)
- DELTA = 0.4 (interval adjustment parameter)
- EPSILON = 0.0000000001 (tiny adjustment to bounds)
- B = confidenceInterval / 100 (e.g., 0.8 for 80%)

CHOOSING LINEAR VS. LOG SCORING:

Use LINEAR scoring (useLogScoring = false) when:
- Quantity has a relatively narrow range (within 1-2 orders of magnitude)
- You think in terms of absolute differences (±X units)
- Examples: temperatures, percentages, heights/weights of similar objects, 
  test scores, years/dates, most everyday measurements

Use LOG scoring (useLogScoring = true) when:
- Quantity spans multiple orders of magnitude (10x, 100x, 1000x+ ranges)
- You think in terms of multiplicative factors or powers of 10
- Examples: populations, GDP/valuations, astronomical/microscopic distances,
  company sizes, wealth distributions, timescales (seconds to years)

Decision heuristic:
- If your interval could reasonably span 10x or more: use LOG
- If you're thinking "±X units": use LINEAR
- If you're thinking "could be 2x-10x higher/lower": use LOG

Why it matters:
- LINEAR: [100, 200] and [1M, 1M+100] have equal width (100), scored similarly
- LOG: [100, 200] (2x) and [1M, 2M] (2x) have equal relative width, scored similarly
         [100, 1000] (10x) is penalized more than [1M, 1.1M] (1.1x)

ALGORITHM:

IF useLogScoring is FALSE (LINEAR MODE):
    1. Adjust bounds slightly:
       lowerBound = lowerBound - EPSILON
       upperBound = upperBound + EPSILON
    
    2. Calculate normalized distances:
       r = (lowerBound - answer) / C
       s = (upperBound - lowerBound) / C
       t = (answer - upperBound) / C
    
    3. Check which case applies:
       
       CASE A: answer < lowerBound (BELOW interval)
           score = max(SMIN, (-2/(1-B)) * r - (r/(1+r)) * s)
       
       CASE B: answer > upperBound (ABOVE interval)
           score = max(SMIN, (-2/(1-B)) * t - (t/(1+t)) * s)
       
       CASE C: lowerBound ≤ answer ≤ upperBound (INSIDE interval)
           a. Adjust bounds with delta:
              lowerBound = lowerBound - DELTA
              upperBound = upperBound + DELTA
           
           b. Recalculate distances with adjusted bounds:
              r = (lowerBound - answer) / C
              s = (upperBound - lowerBound) / C
              t = (answer - upperBound) / C
           
           c. Calculate score:
              score = (4 * SMAX * r * t) / (s * s) * (1 - s/(1+s))

ELSE IF useLogScoring is TRUE (LOGARITHMIC MODE):
    1. Adjust bounds multiplicatively:
       lowerBound = lowerBound / (10^EPSILON)
       upperBound = upperBound * (10^EPSILON)
    
    2. Calculate log-normalized distances:
       r = log(lowerBound / answer) / log(C)
       s = log(upperBound / lowerBound) / log(C)
       t = log(answer / upperBound) / log(C)
    
    3. Check which case applies:
       
       CASE A: answer < lowerBound (BELOW interval)
           score = max(SMIN, (-2/(1-B)) * r - (r/(1+r)) * s)
       
       CASE B: answer > upperBound (ABOVE interval)
           score = max(SMIN, (-2/(1-B)) * t - (t/(1+t)) * s)
       
       CASE C: lowerBound ≤ answer ≤ upperBound (INSIDE interval)
           a. Adjust bounds with delta:
              lowerBound = lowerBound / (10^DELTA)
              upperBound = upperBound * (10^DELTA)
           
           b. Recalculate log distances with adjusted bounds:
              r = log(lowerBound / answer) / log(C)
              s = log(upperBound / lowerBound) / log(C)
              t = log(answer / upperBound) / log(C)
           
           c. Calculate score:
              score = (4 * SMAX * r * t) / (s * s) * (1 - s/(1+s))

RETURN score

ADDITIONAL NOTES:
- When answer is inside interval: tighter intervals score higher
- When answer is outside: larger misses are penalized more heavily
- The penalty for being outside scales with (1-B), so higher confidence intervals risk more
- C parameter controls overall sensitivity (larger C = less sensitive to errors)

---

BINARY SCORING (Log Scoring Rule):

INPUTS:
- estimate: probability assigned to event (0 to 1)
- resolution: true/false outcome

ALGORITHM:
likelihoodAssignedToOutcome = resolution ? estimate : (1 - estimate)
score = (log(likelihoodAssignedToOutcome) - log(0.5)) * 10

RETURN score

NOTES:
- Score ranges from -∞ (assigned 0% to outcome that happened) to +10 (100% confidence, correct)
- 50% confidence always scores 0 regardless of outcome
- Proper scoring rule: maximized by reporting true beliefs
