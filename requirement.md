Required Modifications
Modification 1: Knowledge Graph–Grounded Interaction Representation
•	Shift from attempted ingredient-level interaction analysis to existing, verified drug and ingredient data only.
•	Represent drug–drug interactions using a Knowledge Graph (KG) to ensure structured and factual interaction modeling.
•	Restrict interaction generation to pre-existing relationships stored in the KG.
•	Eliminate inference of non-existent ingredients or unsupported interactions.
•	turn off Groq and turn on  Ollma 
•	Need to add the ingredients for few data points need for active and inactive ingredients (need to display)

Modification 2: Hallucination Detection and Control Mechanism
•	Define hallucination as any interaction output does not present in the Knowledge Graph.
•	Introduce a fact-checking layer to validate all generated interactions against the KG.
•	Implement a hallucination detection metric to measure the percentage of unsupported interaction claims.
•	Control hallucination by enforcing KG-constrained generation, suppressing or rejecting unverifiable outputs.
•	Ensure model responses explicitly state when no verified interaction exists.


