# Model integration


`care/model_ports.py` exposes `classify_note(text)` and `generate_response(text, context)`. Both return `None` until the evaluated models are connected. The application supplies recent conversation context, stores available classification results, and uses explicit rules and scripted replies meanwhile. It never invents model confidence or a diagnosis.

The hybrid decision uses evidence from distinct layers within seven days. Tier-1 keywords override consensus; the proposal's explicit sudden-drop, consecutive-low-weekly-mood and disengagement rules remain standalone review paths. See the proposal comparison for this interpretation and the requirements still awaiting model evaluation.

