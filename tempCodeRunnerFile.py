import os
import shutil
import customtkinter as ctk
from tkinter import filedialog, simpledialog, Canvas, PhotoImage, NW
import spacy

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

nlp = spacy.load("en_core_web_sm")

operation_sessions = []

def get_desktop_path():
    if os.name == 'nt':
        return os.path.join(os.environ['USERPROFILE'], 'Desktop')
    else:
        return os.path.join(os.environ['HOME'], 'Desktop')

def get_documents_path():
    if os.name == 'nt':
        return os.path.join(os.environ['USERPROFILE'], 'Documents')
    else:
        return os.path.join(os.environ['HOME'], 'Documents')

def get_downloads_path():
    if os.name == 'nt':
        return os.path.join(os.environ['USERPROFILE'], 'Downloads')
    else:
        return os.path.join(os.environ['HOME'], 'Downloads')

def parse_command(command):
    doc = nlp(command.lower())
    action = None
    target = None
    path = None
    folder_names = []
    base_dir = None
    nested_dir = None
    folder_name_mode = False
    nested_dir_mode = False

    print(f"Analyzing command: {command}")

    for token in doc:
        print(f"Token: {token.text}, POS: {token.pos_}, DEP: {token.dep_}, Head: {token.head.text}")  # Detailed token info
        if token.dep_ == 'ROOT' or (token.dep_ == 'aux' and token.head.dep_ == 'ROOT'):
            action = token.lemma_
        elif token.dep_ in ['dobj', 'pobj'] and token.head.lemma_ in ['create', 'organize', 'undo']:
            target = token.text
        elif token.text in ['desktop', 'documents', 'downloads']:
            base_dir = token.text
        elif token.text == 'named':
            folder_name_mode = True
        elif folder_name_mode and token.pos_ in ['PROPN', 'NOUN', 'X']:
            folder_names.append(token.text)
        elif token.pos_ in ['PUNCT', 'CCONJ']:
            folder_name_mode = False
        elif token.text == 'in' and base_dir:
            nested_dir_mode = True
        elif nested_dir_mode and token.pos_ in ['PROPN', 'NOUN', 'X']:
            nested_dir = token.text
            nested_dir_mode = False

    if base_dir == 'desktop':
        path = get_desktop_path()
    elif base_dir == 'documents':
        path = get_documents_path()
    elif base_dir == 'downloads':
        path = get_downloads_path()

    if nested_dir:
        path = os.path.join(path, nested_dir)

    # Handle comma-separated folder names correctly
    if 'named' in command.lower():
        named_index = command.lower().index('named') + 6
        folder_string = command[named_index:].split('in')[0]
        folder_names = [name.strip() for name in folder_string.split(',')]

    return action, target, path, folder_names

def execute_command(action, target, path, folder_names):
    if action == "create" and target in ["folders", "folder"]:
        if path:
            if folder_names:
                current_session = []
                for folder_name in folder_names:
                    folder_path = os.path.join(path, folder_name.strip())
                    create_folder(folder_path, current_session)
                operation_sessions.append(current_session)
                show_success_message(f"Folders created: {', '.join(folder_names)} at {path}")
            else:
                show_success_message("No folder names provided.")
        else:
            show_error_message("Path not recognized.")
    elif action == "create" and target == "files":
        if path and folder_names:
            current_session = []
            for file_name in folder_names:
                file_path = os.path.join(path, file_name.strip() + '.txt')
                create_file(file_path, current_session)
            operation_sessions.append(current_session)
            show_success_message(f"Files created: {', '.join(folder_names)}.txt at {path}")
        else:
            show_error_message("Path or file names not recognized.")
    elif action == "organize" and path:
        organize_files_by_extension(path)
        show_success_message(f"Organizing files in {path}.")
    elif action == "undo":
        start_undo()
    elif action == "quit":
        start_shutdown()
    else:
        show_error_message("Command not recognized or incomplete")

def parse_and_execute_command(event=None):
    command = search_entry.get().lower()
    if command == "quit":
        start_shutdown()
    else:
        action, target, path, folder_names = parse_command(command)
        start_execution(action, target, path, folder_names)

def move_file(source, destination, current_session):
    shutil.move(source, destination)
    current_session.append(('move', {'source': source, 'destination': destination}))

def create_folder(path, current_session):
    if not os.path.exists(path):
        os.makedirs(path)
        current_session.append(('create', {'path': path}))

def create_file(path, current_session):
    if not os.path.exists(path):
        with open(path, 'w') as file:
            file.write("")
        current_session.append(('create_file', {'path': path}))

def undo_last_operation():
    if operation_sessions:
        last_session = operation_sessions.pop()
        for operation_type, operation in reversed(last_session):
            if operation_type == 'move':
                os.makedirs(os.path.dirname(operation['source']), exist_ok=True)
                shutil.move(operation['destination'], operation['source'])
            elif operation_type == 'create':
                if os.path.isdir(operation['path']) and not os.listdir(operation['path']):
                    os.rmdir(operation['path'])
            elif operation_type == 'create_file':
                if os.path.isfile(operation['path']):
                    os.remove(operation['path'])
        show_success_message("Last operation session undone.")
    else:
        show_success_message("No operations to undo.")

def start_undo():
    global running_animation, dot_count
    running_animation = True
    dot_count = 1
    search_entry.pack_forget()
    label.pack(pady=40)
    animate_text("Undoing Previous Actions")
    root.after(3000, undo_last_operation)

def organize_files_by_extension(folder_path):
    file_categories = {
        'PDFs': ['.pdf'],
        'Images': ['.jpeg', '.jpg', '.png'],
        'Videos': ['.mp4', '.mov'],
        'Text': ['.txt', '.docx'],
        'Compressed': ['.zip', '.rar'],
        'Install Files': ['.dmg'],
        'Music': ['.mp3']
    }
    created_folders = {}
    misc_files = []
    current_session = []

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path):
            file_ext = os.path.splitext(item)[1].lower()
            matched_category = None
            for category, extensions in file_categories.items():
                if file_ext in extensions:
                    matched_category = category
                    subfolder_path = os.path.join(folder_path, category)
                    if subfolder_path not in created_folders:
                        os.makedirs(subfolder_path, exist_ok=True)
                        created_folders[subfolder_path] = True
                    shutil.move(item_path, os.path.join(subfolder_path, item))
                    current_session.append(('move', {'source': item_path, 'destination': os.path.join(subfolder_path, item)}))
                    break
            if not matched_category:
                misc_files.append(item_path)
    if misc_files:
        misc_path = os.path.join(folder_path, 'Misc')
        if not os.path.exists(misc_path):
            os.makedirs(misc_path, exist_ok=True)
        for file_path in misc_files:
            shutil.move(file_path, os.path.join(misc_path, os.path.basename(file_path)))
            current_session.append(('move', {'source': file_path, 'destination': os.path.join(misc_path, os.path.basename(file_path))}))

    if current_session:
        operation_sessions.append(current_session)
        show_success_message("Files and folders have been organized.")
    else:
        show_error_message("No files found to organize.")

def start_shutdown():
    global running_animation, dot_count
    running_animation = True
    dot_count = 1
    search_entry.pack_forget()
    label.pack(pady=40)
    animate_text("Shutting down")
    root.after(3000, root.quit)

# UI functions
def show_success_message(message):
    global running_animation
    running_animation = False
    label.configure(text=f"{message} ✅")
    root.after(3000, reset_interface)

def show_error_message(message):
    global running_animation
    running_animation = False
    label.configure(text=f"{message} ❌")
    root.after(3000, reset_interface)

def reset_interface():
    label.pack_forget()
    search_entry.pack(pady=20)
    search_entry.delete(0, ctk.END)
    search_entry.pack(pady=20)

def animate_text(text):
    global dot_count
    if running_animation:
        dots = '.' * dot_count
        label.configure(text=f"{text}{dots}")
        dot_count = (dot_count % 3) + 1
        root.after(500, lambda: animate_text(text))

def start_execution(action, target, path, folder_names):
    global running_animation, dot_count
    running_animation = True
    dot_count = 1
    search_entry.pack_forget()
    label.pack(pady=40)
    animate_text("Executing")
    root.after(3000, lambda: execute_command(action, target, path, folder_names))

def select_folder_and_create():
    file_or_folder = simpledialog.askstring("Create", "Do you want to create a folder or file?")
    if file_or_folder:
        names = simpledialog.askstring("Names", f"Enter {file_or_folder}(s) name(s) (comma separated):")
        if names:
            path = filedialog.askdirectory()
            if path:
                folder_names = [name.strip() for name in names.split(',')]
                action = "create"
                target = "files" if "file" in file_or_folder.lower() else "folders"
                start_execution(action, target, path, folder_names)
            else:
                show_error_message("No directory selected.")
        else:
            show_error_message("No names provided.")
    else:
        show_error_message("No selection made.")

def select_folder_and_organize():
    path = filedialog.askdirectory()
    if path:
        start_execution("organize", None, path, [])
    else:
        show_error_message("No directory selected.")

# Enhanced UI
def create_gui():
    global root, search_entry, label, bg_image

    root = ctk.CTk()
    root.title("File Organizer")
    window_width = 500
    window_height = 550 
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width / 2 - window_width / 2)
    center_y = int(screen_height / 2 - window_height / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    # Create Canvas for background image
    canvas = Canvas(root, width=window_width, height=window_height)
    canvas.pack(fill="both", expand=True)

    # Load the background image
    bg_image = PhotoImage(file=r"D:/OS Project 2/assets/img.png")  # Replace with your image path
    canvas.create_image(0, 0, image=bg_image, anchor=NW)

    button_size = 100
    spacing = 30
    total_button_width = button_size * 3 + spacing * 2
    start_x = window_width // 2 - total_button_width // 2

    organize_button = ctk.CTkButton(root, text="Organize", fg_color="black", hover_color="green", command=select_folder_and_organize, width=button_size, height=button_size)
    organize_button.place(x=start_x, y=40)

    generate_folders_button = ctk.CTkButton(root, text="Generate", fg_color="black", hover_color="orange", command=select_folder_and_create, width=button_size, height=button_size)
    generate_folders_button.place(x=start_x + button_size + spacing, y=40)

    undo_button = ctk.CTkButton(root, text="Undo", fg_color="black", hover_color="red", command=start_undo, width=button_size, height=button_size)
    undo_button.place(x=start_x + 2 * button_size + 2 * spacing, y=40)

    search_entry = ctk.CTkEntry(root, placeholder_text="Enter Command", width=280, height=30)
    search_entry.place(relx=0.5, rely=0.9, anchor="s")
    search_entry.bind("<Return>", parse_and_execute_command)

    label = ctk.CTkLabel(root, text="", font=("Arial", 16), text_color="#FFFFFF", padx=10, pady=10)
    label.pack_forget()  # Initially hidden

    root.mainloop()

if __name__ == "__main__":
    create_gui()
