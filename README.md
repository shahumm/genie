# GENIE: An AI-powered File Management System

<img src="https://github.com/user-attachments/assets/df725480-406f-49ef-8d1a-588877c23d39" alt="Gemini-Logo" width="150"/>

### Overview
For our semester-end project, we developed a Google Gemini-powered file manager that simplifies file management. It swiftly organizes large folders, creates nested folders using natural language commands, and sends files directly via email. Additionally, it can generate custom outputs with Google Gemini, ready to attach to emails.

![193shots_so](https://github.com/user-attachments/assets/d18a7a77-8d5a-43c0-8cba-0ea9856f8d59)

## Commands
#### CREATING

    - Create files named <filename(s)> in <location = documents, downloads, desktop>
    - Create folders named <filename(s)> in <location = documents, downloads, desktop>
    - Undo (to undo the last action)
    - Quit (to exit the app)

#### ORGANIZING

    - Organize <location> (to organize all files in a specific location)
    - Organize in <foldername> in <location> (to organize files into a specific folder)

#### EMAILING

    - Send <file.txt/folder> in <location = documents, downloads, desktop> to <email/icloud>

#### GEMINI

    - Generate prompt (to create a prompt using Google Gemini)
    - Write response to file <filename> (saves the response as a text file in the current project directory)
    - Send response to <email/icloud> (to email the generated response)
