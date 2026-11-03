# YAMNet Sound Classification & Evaluation

## Main takeaways (You must write this section manually and without AI assistance. The purpose is for you to reflect on what you did and practice articulating that for others.)
- YAMNet setup: Used TensorFlow’s official YAMNet tutorial notebook as the template, then added my own recordings and tests.
- Dataset collection: Recorded 31 sounds across 10 categories, with 3 takes of each (2 being ~3 seconds, 1 being ~1 second) plus one mixed-noise water recording.
- Audio preprocessing: Converted the M4A files to 16 kHz mono WAV with FFmpeg (the format YAMNet needs).
- Batch testing: Ran all 31 recordings through YAMNet and saved the top 3 labels and scores for each to a CSV file.
- Results: The correct label was the top prediction for 7 of 30 recordings (23.3%) and in the top 3 for 13 of 30 (43.3%). Only 3 of 10 sound types got the same top label across their first 2 takes. (Preliminary)
- Restricted Label Experiment: Tested 20 selected labels; 8/31 predictions changed, but they weren't consistently better.
- Embedding-based Classification: Used YAMNet embeddings, cosine similarity, and nearest-neighbor classification. Obtained 27/30 (90%) in leave-one-out testing.
- Reference Testing: Tested one reference per category across three trials: 85%, 90%, and 75%.
- Short-clip Testing: Tested 1.0s, 0.5s, and 0.2s clips, obtaining 80%, 83.3%, and 40% respectively. 
- Limitations: YAMNet struggled with keys, clapping, and pen clicks. Not yet tested: sub-second clips (mine ran 1.07 to 4.35 seconds), other devices for recording sounds, and how well labels map to musical roles. Small dataset, similar recording conditions, silence-padding effects, and why manual classification should remain available. The 90% result was based on over 30 recordings where they were recorded in similar conditions and with the same objects (eg. keys jingling were recorded with the same set of keys in the same room) so it may not work as well with new users' sounds
adding silence and comparing short clips against longer recordings could've affected the accuracy in the short clip results
- Deliverables: Completed notebook, results CSV, and the shared recordings.

## Resource Usage

Tool and Model(s) Used: ChatGPT (GPT-6)
- Purpose: Since the project used a pre-existing YAMNet tutorial/template, my main work involved recording audio samples, writing test functions for batch evaluation, and analyzing the model's predictions. Used ChatGPT to review my original YAMNet notebook and troubleshoot code. ChatGPT also helped interpret the results additional experiments (involving restricted labels, audio embeddings, nearest-neighbor classification, and short-clip testing) , identify methodological limitations, and review the conclusions.
- Tokens Used & Dollar Equivalent: Exact token usage unavailable. Used ChatGPT with no additional per-request or API charges.

## Chat Log
https://chatgpt.com/share/6ae9f47b-c8e4-83ea-8f4f-6e67ffae90b4

