## Project Description

This was a game similar to the word game Hangman. Using Custom markers, we created flashcards representing the alphabets of the English dictionary. The player is playing against Cozmo in this game, where Cozmo is trying to guess the word that the player chooses. The players are given flashcards to arrange on a stand in front of Cozmo. The letters are all facing the player when the game starts, but as and when Cozmo guesses the correct letter, the player turns those cards. Cozmo gets 9 tries to guess the word.

## Video

[https://www.youtube.com/watch?v=lKHcDP6F1N0](https://www.youtube.com/watch?v=lKHcDP6F1N0)

## Implementation Details

This game utilizes the Custom Markers provided by the SDK. The addition of 16 custom markers was a great help in creating this game. We used the same marker on the back of each card for Cozmo to know how long the length of the word is and each letter had a corresponding marker on the front. Cozmo also displays the letter he guesses on his face, so as to not create any confusion. We used "display_oled_face_image" for this. 

## Instructions

There are a few dependencies on other Python libraries for this project: 
PIL was used to convert text into an image and display it on Cozmo's OLED face
Wizards of Coz Common folder found [here](https://github.com/Wizards-of-Coz/Common)

## Thoughts for the Future
The current version of the game is single player where you are playing against Cozmo. This could be converted into a multiplayer game where multiple people are playing with Cozmo to see who has the smarter Cozmo! It could also be converted into a game wherein Cozmo thinks of a word and the player is required to guess it. This would create an interesting challenge for the player. 
