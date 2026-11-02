

# Test generating drum patterns with Fermata. Build interface 

## Main takeaways (You must write this section manually and without AI assistance. The purpose is for you to reflect on what you did and practice articulating that for others.)

* Fermata does have the parameter capability that we are looking for.
* Can easily input parameters like genre and bpm to modify results.
* It doesn't necessarily sound good
* This could be due to human error. The json mapping of sounds to the MIDI was done by a human so the bass sound may have been playing where the kick should have etc.
* The library of models available for text to MIDI is limited in comparison to the library of models for text to audio.
* Could look into using these text to audio models, convert the output audio to MIDI, and map the sounds to that MIDI
* Might result in better music quality/ beat quality
* Music gen is a possible model for this task
* This is more compute intensive than just fermata. 
* Music gen also struggles with human language according to the models developers which could be beneficial on the moderation side.
* Allows for much more natural text from the user vs strict parameters with fermata.
* Audio output samples provided for team review.
* Overall, I set up a way to interact with Fermata and to apply sounds to the MIDI generated in a rudimentary way which helped to test the models capabilities.
* Outlook/future: decide if fermata results are good enough or if it is worth pursuing the other sequencing strategy.

## Resource Usage

ChatGPT was used as the AI tool

Tokens Used & Dollar Equivalent:
ChatGPT doesn't offer native support for token/ dollar equivalent usage amount. 
I do have ChatGPT plus as part of a free program for students.
I did not reach any usage limits though. 

## Chat Log

(Paste the full chat history from the session).
Multiple chat histories. Public Links provided below for conciseness.
Chat Links:
Fermata wrapper - https://chatgpt.com/share/6adbf210-c7a8-83ea-92cb-078af979ea8a
Apply Sound to MIDI - https://chatgpt.com/share/6adbf4fe-feec-83ea-9e39-7e08fa16d7a8 
Music Gen wrapper - https://chatgpt.com/share/6adc044c-e2c8-83ea-8f3a-4cba048ea882 
Song To MIDI - 
Possible future direction. Use Music Gen to create an audio file, convert that to MIDI, apply sounds to that MIDI.
Song to MIDI not implemented thus no link as this chat does not exist