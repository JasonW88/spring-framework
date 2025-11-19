import sys
from pathlib import Path
import re

COMMON = "/spring-framework/"

def normalize_checker_error(error_text):
    """
    Replaces capture class numbers (e.g., capture#01428)
    with a consistent placeholder (capture#N) for stable comparison.
    """
    # Regex pattern: 'capture#' followed by one or more digits (\d+).
    pattern = r"capture#\d+"
    # Replace all matches of the pattern with 'capture#N'
    normalized_text = re.sub(pattern, "capture#N", error_text)
    
    return normalized_text

if(len(sys.argv) != 3):
    print("Usage: python error_compare.py [error_log_path1] [error_log_path2]")
    quit()

error_log1 = sys.argv[1]
error_log2 = sys.argv[2]
log1_path = Path(error_log1)
log2_path = Path(error_log2)

if(not log1_path.is_file()):
    print(f"Error: cannot find {error_log1}, check if path is correct")
    quit(1)
if(not log2_path.is_file()):
    print(f"Error: cannot find {error_log2}, check if path is correct")
    quit(1)

with open(error_log1) as e_log1_f:
    log1_contents = e_log1_f.read()

with open(error_log2) as e_log2_f:
    log2_contents = e_log2_f.read()

log1_contents = normalize_checker_error(log1_contents)
log2_contents = normalize_checker_error(log2_contents)
log1_contents = re.sub(r'(\r?\n){2,}', r'\n', log1_contents)
log2_contents = re.sub(r'(\r?\n){2,}', r'\n', log2_contents)
log1_contents = re.sub(r'^\> Task :.*\n?', '', log1_contents, flags=re.MULTILINE)
log2_contents = re.sub(r'^\> Task :.*\n?', '', log2_contents, flags=re.MULTILINE)

#prefix analysis (log 1's prefix will be transformed into log 2's)

log1_prefix_end = log1_contents.find(COMMON)
#goto start of line
log1_prefix_start = log1_contents[:log1_prefix_end].rfind("\n") 
log1_prefix = log1_contents[log1_prefix_start+1:log1_prefix_end]
print(f"Prefix log 1: {log1_prefix}")
log2_prefix_end = log2_contents.find(COMMON)
#goto start of line
log2_prefix_start = log2_contents[:log2_prefix_end].rfind("\n") 
log2_prefix = log2_contents[log2_prefix_start+1:log2_prefix_end]
print(f"Prefix log 2: {log2_prefix}")

#prefix unification (find and replace)
log1_contents_modified = log1_contents.replace(log1_prefix, log2_prefix)

#error carving (into list of strings)
#errors are either normal CF error that begin with /.../path-to-source-code-being-checked/...
#or start with "error:"
set_e1 = set()
set_e2 = set()
def carve_errors_add_set(error_set : set, error_str : str, error_prefix : str):
    e_lines = error_str.splitlines()
    current_error = ""
    started = False

    for i in range(len(e_lines)):
        if(e_lines[i].strip() == ""):
            continue
        if(started):
            #final error terminated by
            pattern1 = r"\d+\s+errors"
            pattern2 = r"\d+\s+warnings"
            match1 = re.search(pattern1, e_lines[i])
            match2 = re.search(pattern2, e_lines[i+1])
            if(e_lines[i].startswith("error: ")):
                #checker framework error
                error_set.add(current_error)
                current_error = f"{e_lines[i]}\n"
            elif(e_lines[i].startswith(error_prefix)):
                error_set.add(current_error)
                current_error = f"{e_lines[i]}\n"
            elif((match1 != None) and (match2 != None)):
                print("found final error, carving complete")
                error_set.add(current_error)
                break
            else:
                #not a new error
                current_error = f"{current_error}{e_lines[i]}\n"
                #concat line
        else:
            if(e_lines[i].startswith("error: ") or e_lines[i].startswith(error_prefix)):
                #checker framework error
                current_error = f"{e_lines[i]}\n"
                started = True

carve_errors_add_set(set_e1, log1_contents_modified, log2_prefix)
carve_errors_add_set(set_e2, log2_contents, log2_prefix)

#difference analysis (by sets)
log1_unique = set_e1 - set_e2
log2_unique = set_e2 - set_e1


with open(f"{log1_path.stem}-unique.txt", "w") as oute1me2:
    oute1me2.writelines(log1_unique)

with open(f"{log2_path.stem}-unique.txt", "w") as oute2me1:
    oute2me1.writelines(log2_unique)
   
print(f"Number of unique errors to {error_log1}:", len(log1_unique))
print(f"Number of unique errors to {error_log2}:", len(log2_unique))