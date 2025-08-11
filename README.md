# A ranking system for IPSC
Currently we only display results for Swedish shooters, but this can be extended to all IPSC shooters.

* The ranking system is based on the [OpenSkill](https://openskill.me/) algorithm.
* With OpenSkill we use the [Bradley-Terry Partial Pairing Model](https://openskill.me/en/latest/api/openskill.models.weng_lin.bradley_terry_part.html) due to the sparse nature of IPSC match results.
* We use the calculated skill together with the uncertainty to calculate a ranking.
* Higher level matches are weighted more heavily than lower level matches.
* Inactive shooters are penalized with a skill decay.

## How it works

* We fetch the match data from the different data sources.
* We use the combined results to update the skill ratings of the shooters using the OpenSkill algorithm.
* We use the calculated skill together with the uncertainty to calculate a ranking.

## Data sources
* [Shoot'n Score It](https://shootnscoreit.com/dashboard/)
* [IPSC Results](https://ipscresults.org/)
* [PracticeScore](https://www.practicescore.com/)

## Frequently Asked Questions

### What is OpenSkill?

[OpenSkill](https://openskill.me/) is a ranking algorithm, published in the paper [A Bayesian Approximation Method for Online Ranking](https://jmlr.org/papers/volume12/weng11a/weng11a.pdf), which has gained popularity in the world of online gaming during the recent years.

OpenSkill is an improvement on the [TrueSkill](https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/) algorithm, publicised in the [TrueSkill paper](https://proceedings.neurips.cc/paper_files/paper/2006/file/f44ee263952e65b3610b8ba51229d1f9-Paper.pdf), which was developed by Microsoft for the Xbox Live ranking system, and first used for matchmaking in the video game Halo.

### Why is OpenSkill a better choice for IPSC than Elo?

OpenSkill is a better choice for IPSC than Elo because it is designed to handle multiplayer games with relative outcomes, whereas Elo is designed to handle two-player games with binary outcomes, where the outcome of a match is either a win or a loss.

In an IPSC match there are multiple participants and the outcome of a match is the relative ranking of the participants. Elo is not designed to handle this type of outcome and will not perform as well as OpenSkill in this context.

### Why is OpenSkill a better choice for IPSC than TrueSkill?

OpenSkill is an improvement on the TrueSkill algorithm, and should perform better, even though it is not as established as TrueSkill. Also OpenSkill has a more permissive license than TrueSkill.

### How does the skill decay work?

The skill decay is based on the time since the last match. The skill uncertainty increases with the time since the last match, for each day since the last match the skill uncertainty increases by a constant. The constant has been optimized to match the observed results of the matches in the system.

### How does the level based weighting work?

The level of the match is used to adjust the beta parameter of the OpenSkill model. The beta parameter can be thought of as the certainty of the outcome. The higher the beta, the more certain the outcome. The beta parameter is adjusted based on the level of the match.

* Level 2 matches have a beta of 25/12
* Level 3 matches have a beta of 25/6
* Level 4 matches have a beta of 25/3
* Level 5 matches have a beta of 25/2.

The reasoning behind this is that the higher the level of the match, the shooters are more likely to do their best, and the results are more reliable.

### Why publish the code?

I want to make sure that the ranking system is transparent and can be verified by anyone. I also want to make sure that the ranking system is not a black box, and that the calculations are done in a way that is easy to understand and verify.

I also want to encourage others to improve the ranking system and make it better.

### What is IPSC?

IPSC is the International Practical Shooting Confederation. It is the governing body for practical shooting sports. Practical shooting is a sport that involves shooting at targets that are placed at various distances and angles. There are different disciplines of practical shooting, the largest discipline is the IPSC Handgun division.

In IPSC Handgun competitors compete in different divisions:
* Production
* Production Optics
* Open
* Standard
* Classic
* Revolver

Often in Handgun matches there is an extra division called Pistol Caliber Carbine (PCC) which is a division for shooters who use a pistol caliber carbine.

There are also different categories based on age and gender:
  
* Super Junior
* Junior
* Senior
* Super Senior
* Grand Senior
* Lady
* Lady Super Junior
* Lady Junior
* Lady
* Lady Senior
* Lady Super Senior
* Lady Grand Senior


### References
* [OpenSkill website](https://openskill.me/)
* [OpenSkill paper](https://jmlr.org/papers/volume12/weng11a/weng11a.pdf)
* [TrueSkill website](https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/)
* [TrueSkill paper](https://proceedings.neurips.cc/paper_files/paper/2006/file/f44ee263952e65b3610b8ba51229d1f9-Paper.pdf)