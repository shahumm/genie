import os
import shutil
import smtplib
import customtkinter as ctk
from tkinter import filedialog, simpledialog, Canvas, PhotoImage, NW, END
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
import spacy
import re
import socket
import google.generativeai as genai
from tkinter.scrolledtext import ScrolledText
import random
import requests  
from PIL import Image, ImageTk  
from io import BytesIO  


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

nlp = spacy.load("en_core_web_sm")

operation_sessions = []
generated_response = None
running_animation = False
dot_count = 0

try:
    os.environ["GEMINI_API_KEY"] = "AIzaSyBhgKVi9VEyCN7VXqnumFc1GlZVHhVBrm0"
    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Failed to configure Gemini API: {e}")

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
    try:
        doc = nlp(command)  
        action = None
        target = None
        path = None
        folder_names = []
        base_dir = None
        nested_dir = None
        email_address = None
        folder_name_mode = False
        nested_dir_mode = False

        print(f"Analyzing command: {command}")

        if command.lower().startswith("generate "):
            action = "generate"
            target = command[9:].strip() 
            return action, target, path, folder_names, email_address
        elif command.startswith("write response to file"):
            action = "write_response"
            target = command.split("file")[1].strip()
            return action, target, path, folder_names, email_address
        elif command.startswith("send response to"):
            action = "send_response"
            target = command.split("to")[1].strip()
            return action, target, path, folder_names, email_address

        for token in doc:
            print(f"Token: {token.text}, POS: {token.pos_}, DEP: {token.dep_}, Head: {token.head.text}")
            if token.dep_ == 'ROOT' or (token.dep_ == 'aux' and token.head.dep_ == 'ROOT'):
                action = token.lemma_
            elif token.dep_ in ['dobj', 'pobj'] and token.head.lemma_ in ['create', 'organize', 'undo', 'send']:
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
            elif token.like_email:
                email_address = token.text

        if base_dir == 'desktop':
            path = get_desktop_path()
        elif base_dir == 'documents':
            path = get_documents_path()
        elif base_dir == 'downloads':
            path = get_downloads_path()

        if nested_dir:
            path = os.path.join(path, nested_dir)

        if 'named' in command.lower():
            named_index = command.lower().index('named') + 6
            folder_string = command[named_index:].split('in')[0]
            folder_names = [name.strip() for name in folder_string.split(',')]

        if action == 'send' and 'to' in command.lower():
            to_index = command.lower().index('to') + 3
            folder_string = command.lower().split('to')[0].split('in')[0].split('send')[1].strip()
            folder_names = [name.strip() for name in folder_string.split(',')]


        if command.lower().startswith("organize "):
            action = "organize"
            if "documents" in command.lower():
                base_dir = "documents"
                path = get_documents_path()
            elif "desktop" in command.lower():
                base_dir = "desktop"
                path = get_desktop_path()
            elif "downloads" in command.lower():
                base_dir = "downloads"
                path = get_downloads_path()
            
            if "in" in command.lower() and base_dir:
                nested_dir = command.lower().split("in")[1].strip()
                path = os.path.join(path, nested_dir)

        return action, target, path, folder_names, email_address
    except Exception as e:
        show_error_message(f"Failed to parse command: {str(e)}")
        return None, None, None, None, None

def execute_command(action, target, path, folder_names, email_address):
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
    elif action in ["create"] and target in ["file", "files"]:
        show_error_message(f"Invalid keyword '{target}' for creating files.")
    elif action == "organize" and path:
        organize_files_by_extension(path)
        show_success_message(f"Organizing files in {path}.")
    elif action == "undo":
        undo_last_operation()
    elif action == "send" and path and email_address and folder_names:
        send_email_with_animation(path, folder_names, email_address)
    elif action == "generate":
        start_generation(target)
    elif action == "write_response":
        write_response_to_file(target)
    elif action == "send_response":
        send_response_via_email(target)
    elif action == "quit":
        start_shutdown()
    else:
        show_error_message("Command not recognized or incomplete")

def start_generation(prompt):
    global running_animation
    running_animation = True
    response_text.delete("1.0", END)
    response_text.insert("1.0", "✨Generating...")
    root.after(100, lambda: generate_text(prompt))

def generate_text(prompt):
    global generated_response, running_animation
    try:
        response = model.generate_content(prompt)
        generated_response = response.text  
        update_response_text(response.text)
        show_success_message("Content generated!")
    except Exception as e:
        show_error_message(f"Failed to generate text: {str(e)}")
    finally:
        running_animation = False

def update_response_text(response):
    response_text.delete("1.0", END)
    response_text.insert(END, response)

def on_response_text_change(event):
    global generated_response
    if response_text.edit_modified(): 
        generated_response = response_text.get("1.0", END).strip()
        response_text.edit_modified(False)  

def write_response_to_file(filename):
    try:
        if generated_response:
            with open(f"{filename}.txt", 'w') as file:
                file.write(generated_response)
            show_success_message(f"Response written to file: {filename}.txt")
        else:
            show_error_message("No generated response to write.")
    except Exception as e:
        show_error_message(f"Failed to write response to file: {str(e)}")

def send_response_via_email(email_address):
    try:
        if generated_response:
            sender_email = "faaizmuzzammil@gmail.com"
            app_password = "cgxm ntmy tmpw sfgf"
            subject = "Generated Response"
            body = generated_response

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email_address
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            if not validate_email(email_address):
                raise ValueError("Recipient email address does not exist")

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, app_password)
            text = msg.as_string()
            server.sendmail(sender_email, email_address, text)
            server.quit()
            show_success_message(f"Email sent to {email_address}")
        else:
            show_error_message("No generated response to send.")
    except Exception as e:
        show_error_message(f"Failed to send email: {str(e)}")

def parse_and_execute_command(event=None):
    command = search_entry.get().lower()
    if command == "quit":
        start_shutdown()
    else:
        action, target, path, folder_names, email_address = parse_command(command)
        if action:
            if action == "generate":
                start_generation(target)
            else:
                start_execution(action, target, path, folder_names, email_address)

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
            elif operation_type == 'create_folder':
                if os.path.isdir(operation['path']):
                    shutil.rmtree(operation['path'])
        if not operation_sessions:
            show_success_message("All previous actions are undone!")
        else:
            show_success_message("Last operation session undone.")
    else:
        show_success_message("No operations to undo.")

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
                        current_session.append(('create_folder', {'path': subfolder_path}))
                    shutil.move(item_path, os.path.join(subfolder_path, item))
                    current_session.append(('move', {'source': item_path, 'destination': os.path.join(subfolder_path, item)}))
                    break
            if not matched_category:
                misc_files.append(item_path)
    if misc_files:
        misc_path = os.path.join(folder_path, 'Misc')
        if not os.path.exists(misc_path):
            os.makedirs(misc_path, exist_ok=True)
            current_session.append(('create_folder', {'path': misc_path}))
        for file_path in misc_files:
            shutil.move(file_path, os.path.join(misc_path, os.path.basename(file_path)))
            current_session.append(('move', {'source': file_path, 'destination': os.path.join(misc_path, os.path.basename(file_path))}))

    if current_session:
        operation_sessions.append(current_session)
        show_success_message("Files and folders have been organized.")
    else:
        show_error_message("No files found to organize.")

def send_email_with_animation(path, folder_names, email_address):
    global running_animation, dot_count
    running_animation = True
    dot_count = 1
    search_entry.place_forget()
    label.pack(pady=40)
    animate_text("Executing")
    root.after(2000, lambda: send_email(path, folder_names, email_address))

def send_email(path, folder_names, email_address):
    sender_email = "faaizmuzzammil@gmail.com"
    app_password = "cgxm ntmy tmpw sfgf"
    subject = "Files You Requested!"
    body = """Dear Recipient,

I hope this email finds you before I do.

Please find the attached file(s) as per your request. If you have any questions or need further assistance, feel free to reach out.

Best regards,
Your friendly neighbourhood AI"""


    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email_address
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        if not validate_email(email_address):
            raise ValueError("Recipient email address does not exist")

        files_exist = True
        for name in folder_names:
            item_path = os.path.join(path, name)
            if not os.path.exists(item_path):
                files_exist = False
                break

        if not files_exist:
            raise FileNotFoundError("One or more files/folders do not exist")

        for name in folder_names:
            item_path = os.path.join(path, name)
            if os.path.isfile(item_path):
                attach_file(msg, item_path)
            elif os.path.isdir(item_path):
                for root, dirs, files in os.walk(item_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        attach_file(msg, file_path)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        text = msg.as_string()
        server.sendmail(sender_email, email_address, text)
        server.quit()
        show_success_message(f"Email sent to {email_address}")
    except FileNotFoundError as fnf_error:
        show_error_message("Mail was not sent because file/folder does not exist")
    except ValueError as ve:
        show_error_message("Recipient email address does not exist")
    except Exception as e:
        show_error_message(f"Failed to send email: {str(e)}")

def attach_file(msg, filepath):
    with open(filepath, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(filepath)}')
        msg.attach(part)

def validate_email(email_address):
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if re.match(regex, email_address):
        domain = email_address.split('@')[1]
        try:
            socket.gethostbyname(domain)
            return True
        except socket.gaierror:
            return False
    return False

def start_shutdown():
    global running_animation, dot_count
    running_animation = True
    dot_count = 1
    search_entry.place_forget()
    label.pack(pady=40)
    animate_text("Shutting down")
    root.after(2000, root.quit)

def show_success_message(message):
    global running_animation
    running_animation = False
    label.configure(text=f"{message} ✅")
    root.after(2000, reset_interface)

def show_error_message(message):
    global running_animation
    running_animation = False
    label.configure(text=f"{message} ❌")
    root.after(2000, reset_interface)

def reset_interface():
    label.pack_forget()
    search_entry.place(relx=0.5, rely=0.9, anchor="center")
    search_entry.delete(0, ctk.END)
    search_entry.place(relx=0.5, rely=0.9, anchor="center")

def animate_text(text):
    global dot_count
    if running_animation:
        dots = '.' * dot_count
        label.configure(text=f"{text}{dots}")
        dot_count = (dot_count % 3) + 1
        root.after(500, lambda: animate_text(text))

def start_execution(action, target, path, folder_names, email_address):
    global running_animation, dot_count
    running_animation = True
    dot_count = 1
    search_entry.place_forget()
    label.pack(pady=40)
    animate_text("Executing")
    root.after(2000, lambda: execute_command(action, target, path, folder_names, email_address))


PYTHON_BLUE = "#3776AB"
PYTHON_YELLOW = "#FFD43B"

commands = [
    "create files file1.txt, file2.txt in documents",
    "send file1.txt in documents to example@example.com",
    "organize in desktop",
    "undo",
    "generate 'A short story about AI'",
    "write response to file response.txt",
    "send response to example@example.com",
    "quit"
]

current_typing_job = None

def on_entry_focus_in(event, widget, color, other_widget, other_color):
    global current_typing_job
    if current_typing_job:
        root.after_cancel(current_typing_job)
        current_typing_job = None
    widget.configure(border_color=color)
    other_widget.configure(border_color=other_color)

def on_entry_focus_out(event, widget, color, other_widget, other_color):
    widget.configure(border_color=color)
    other_widget.configure(border_color=other_color)
    display_random_command()


def unfocus(event):
    root.focus()  

def type_command(widget, command, index=0):
    global current_typing_job
    if index < len(command):
        current_text = widget.cget("placeholder_text") + command[index]
        widget.configure(placeholder_text=current_text)
        current_typing_job = root.after(100, type_command, widget, command, index + 1)
    else:
        current_typing_job = root.after(3000, display_random_command)

def display_random_command():
    global current_typing_job
    if not search_entry.focus_get() == search_entry:
        search_entry.configure(placeholder_text="")  
        random_command = random.choice(commands)
        type_command(search_entry, random_command)

def create_gui():
    global root, search_entry, label, bg_image, response_text, generated_response

    root = ctk.CTk()
    root.title("GENIE")
    window_width = 640
    window_height = 600
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width / 2 - window_width / 2)
    center_y = int(screen_height / 2 - window_height / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    root.resizable(False, False)

    canvas = Canvas(root, width=window_width, height=window_height)
    canvas.pack(fill="both", expand=True)


    image_url = "https://res.cloudinary.com/dw095oyal/image/upload/v1717716757/TkinterBG_cahzz5.png"

    try:
        response = requests.get(image_url)
        response.raise_for_status()  
        img_data = response.content
        pil_image = Image.open(BytesIO(img_data))
        
        original_width, original_height = pil_image.size
        aspect_ratio = original_height / original_width
        if original_width > window_width or original_height > window_height:
            if (window_width / original_width) < (window_height / original_height):
                new_width = window_width
                new_height = int(new_width * aspect_ratio)
            else:
                new_height = window_height
                new_width = int(new_height / aspect_ratio)
        else:
            new_width, new_height = original_width, original_height
        
        pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
        bg_image = ImageTk.PhotoImage(pil_image)
        canvas.create_image(0, 0, image=bg_image, anchor=NW)
        print(f"Image loaded and displayed: {new_width}x{new_height}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch image: {e}")
    except Exception as e:
        print(f"Failed to load image: {e}")

    canvas.bind("<Button-1>", unfocus)

    response_text = ctk.CTkTextbox(root, fg_color="black", bg_color="black", border_color="gray", width=400, height=200, border_width=1.5)
    response_text.place(relx=0.5, rely=0.62, anchor="center")
    response_text.bind("<<Modified>>", on_response_text_change)
    response_text.bind("<FocusIn>", lambda event: on_entry_focus_in(event, response_text, PYTHON_BLUE, search_entry, PYTHON_YELLOW))
    response_text.bind("<FocusOut>", lambda event: on_entry_focus_out(event, response_text, "gray", search_entry, "gray"))



    
    generated_response = response_text.get("1.0", END).strip() 

    search_entry = ctk.CTkEntry(root, fg_color="black", bg_color="black", border_color="gray", placeholder_text="", width=400, height=30, border_width=1.5)
    search_entry.place(relx=0.5, rely=0.9, anchor="center")
    search_entry.bind("<FocusIn>", lambda event: on_entry_focus_in(event, search_entry, PYTHON_YELLOW, response_text, PYTHON_BLUE))
    search_entry.bind("<FocusOut>", lambda event: on_entry_focus_out(event, search_entry, "gray", response_text, "gray"))
    search_entry.bind("<Return>", parse_and_execute_command)

    label = ctk.CTkLabel(root, text="", font=("Arial", 16), text_color="white", padx=10, pady=10)
    label.pack_forget()

    display_random_command() 

    root.mainloop()

if __name__ == "__main__":
    create_gui()




####################################### COMMANDS ####################################################

# CREATING
# create files named <filename/filenames separated by commas> in <location = documents, downloads, desktop>
# create folders named <filename/filenames separated by commas> in <location = documents, downloads, desktop>
# undo
# quit

# ORGANIZING
# organize location
# organize in foldername in location

# EMAILING
# send file.txt/folder in <location = documents, downloads, desktop> to <email/icloud>

# GEMINI
# generate prompt
# If you want to edit response, edit directly from the textbox and then use the commands below or use them directly. 
# write response to file <filename> (saves txt to the project's current directory)
# send response to <email/icloud>