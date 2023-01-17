import os

file_path = "C:\\Users\\asaf4\\OneDrive\\Desktop\\ClientFolder\\Instructions.txt"

dir_name = os.path.dirname(file_path)
print(dir_name)     # output: C:\Users\asaf4\OneDrive\Desktop\ClientFolder
base_name = os.path.basename(file_path)
print(base_name)    # output: Instructions.txt
