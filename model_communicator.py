from alpaca_turbo import Assistant
import logging
import os
from rich.logging import RichHandler
import signal
import pdb
import pandas as pd
from rich import print as eprint
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import sys

def delete_previous_instance(context):
    FORMAT = "%(message)s"
    logging.basicConfig(
        level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )
    log = logging.getLogger("rich")
    file_name = "./pid" + "_" + context
    if os.path.exists(file_name):
        log.info("Other checks")
        log.fatal("Already running another instance or dirty exit last time")
        with open(file_name) as file:
            pid = int(file.readline())
        log.info("Attempting to kill the process")
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        os.remove(file_name)
        log.info("Fixed the Issue Now Retry running")
        # exit()

def initilize_assistants(model_type, student_context, tutor_context, skip_student_length = 6, skip_tutor_length = 5):
    delete_previous_instance("student")
    delete_previous_instance("tutor")
    
    if model_type == "tuned":
        tutor_model_path = "models/tutor/ggml-model-q4_0.bin"
        student_model_path = "models/student/ggml-model-q4_0.bin"
    elif model_type == "base":
        tutor_model_path = "models/base/ggml-model-q4_0.bin"
        student_model_path = "models/base/ggml-model-q4_0.bin"
    
    tutor_assistant = Assistant(tutor_model_path, tutor_context, "Tutor:", skip_student_length, skip_tutor_length)
    tutor_assistant.prep_model()
    
    student_assistant = Assistant(student_model_path, student_context, "Student:", skip_student_length, skip_tutor_length)
    student_assistant.prep_model()
    
    return student_assistant, tutor_assistant

def get_first_input(file_name):
    with open(file_name, 'r') as file:
        lines = file.readlines()

    return lines[-2].strip()

def copy_to_partial_context_files(student_file, tutor_file, partial_student_file, partial_tutor_file):
    with open(student_file, 'r') as sf:
        student_file_contents = sf.read()

    with open(tutor_file, 'r') as tf:
        tutor_file_contents = tf.read()

    with open(partial_student_file, 'w') as psf:
        lines = student_file_contents.splitlines()
        student_file_contents = '\n'.join(lines[:-1])
        psf.write(student_file_contents)
        psf.write(f"\n")

    with open(partial_tutor_file, 'w') as ptf:
        lines = tutor_file_contents.splitlines()
        tutor_file_contents = '\n'.join(lines[:-1])
        ptf.write(tutor_file_contents)
        ptf.write(f"\n")

def main(grade, model_type):
    base_tutor_directory = f"prompts/{grade}/tutor"
    base_results_directory = f"results/{model_type}"
    base_partial_context_directory = "partial_context"
    
    for file in os.listdir(base_tutor_directory):
        if os.path.isfile(os.path.join(base_tutor_directory, file)) and not os.path.isfile(os.path.join(base_results_directory, file.replace(".txt", "") + "_" + grade + ".csv")):
            tutor_file = os.path.join(base_tutor_directory, file)
            student_file = os.path.join(base_tutor_directory.replace("tutor", "student"), file)
            
            result_data = pd.DataFrame(columns=["role", "conversation", "cefr"])
            # last line of student will be first line of tutor
            student_response = get_first_input(student_file).replace("Student: ", "")
            
            partial_student_file = os.path.join(base_partial_context_directory, file.replace(".txt", "") + "_" + "student.txt")
            partial_tutor_file = os.path.join(base_partial_context_directory, file.replace(".txt", "") + "_" + "tutor.txt")
            
            skip_context = 0
            need_reset = False
            if os.path.isfile(partial_student_file) or os.path.isfile(partial_tutor_file):
                with open(partial_tutor_file, 'a') as f:
                    f.write(f"Student:\n")
                
                with open(partial_student_file, 'a') as f:
                    f.write(f"Tutor:\n")
                
                # Update result data with partial context data 
                with open(partial_student_file, 'r') as f:
                    student_conversation = f.readlines()
                    skip_context = len(student_conversation)
                    # Remove first 8 lines
                    student_conversation = student_conversation[8:]
                    # For rest of the conversation, update the csv data
                    for i in range(0, len(student_conversation) - 1, 2):
                        new_row = {"role": "tutor", "conversation": student_conversation[i].replace("Tutor: ", ""), "cefr": grade}
                        result_data = result_data.append(new_row, ignore_index=True)
                        
                        new_row = {"role": "student", "conversation": student_conversation[i+1].replace("Student: ", ""), "cefr": grade}
                        result_data = result_data.append(new_row, ignore_index=True)
                
                student_response = get_first_input(partial_student_file).replace("Student: ", "")
                student, tutor = initilize_assistants(model_type, partial_student_file, partial_tutor_file, skip_context - 3, skip_context - 4)
                
                need_reset = True
            else:
                student, tutor = initilize_assistants(model_type, student_file, tutor_file)
                # Save partial context in a text file
                # Copy contents to partial context files
                copy_to_partial_context_files(student_file, tutor_file, partial_student_file, partial_tutor_file)
            
            print("File: " + file)
            if skip_context != 0:
                iterate_until = 10 - (len(result_data) / 2)
            else:
                iterate_until = 10
            
            for i in range(int(iterate_until)):
                tutor_response = tutor.ask_bot("Student: " + student_response, i, "")
                new_row = {"role": "tutor", "conversation": tutor_response, "cefr": grade}
                result_data = result_data.append(new_row, ignore_index=True)
                
                # Reset the last line now
                if need_reset:
                    copy_to_partial_context_files(partial_student_file, partial_tutor_file, partial_student_file, partial_tutor_file)
                    need_reset = False
                
                with open(partial_tutor_file, 'a') as f:
                    f.write(f"Student: {student_response}\n")
                    f.write(f"Tutor: {tutor_response}\n")
                print("Tutor: " + tutor_response)
                    
                student_response = student.ask_bot("Tutor: " + tutor_response, i, "")
                new_row = {"role": "student", "conversation": student_response, "cefr": grade}
                result_data = result_data.append(new_row, ignore_index=True)
                with open(partial_student_file, 'a') as f:
                    f.write(f"Tutor: {tutor_response}\n")
                    f.write(f"Student: {student_response}\n")
                print("Student: " + student_response)
                
                print("Conversation Left: " + str(iterate_until - i))

            file_name = file.replace(".txt", "")
            result_data.to_csv(f"{base_results_directory}/{file_name}_{grade}.csv", index=False)
            if os.path.isfile(partial_student_file):
                os.remove(partial_student_file)
                os.remove(partial_tutor_file)

if __name__ == "__main__":
    print("Booting up models")
    if len(sys.argv) > 2:
        arg2 = sys.argv[2]
    else:
        arg2 = "tuned"
    main(sys.argv[1], arg2)
