import os
import shutil
import hashlib
import time
from datetime import datetime

# importing functions from my other files
from folder_setup import check_file, generate_report, create_folders
from extractor import extract_text
from classifier import load_model, classify_document

# i store file hashes here to detect duplicates
# hash is like a unique fingerprint for each file
# same file uploaded twice = same fingerprint = duplicate
processed_hashes = set()

# loading model once when pipeline starts
# no need to reload it for every single file
print("loading model...")
model, vectorizer = load_model()


def get_file_hash(file_path):
    # i learned about md5 hashing to detect duplicates
    # it creates a unique fingerprint based on file content
    # even if filename is different same content = same hash
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        # reading in chunks so large files dont crash memory
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_duplicate(file_path):
    # comparing file fingerprint to ones we already processed
    file_hash = get_file_hash(file_path)
    if file_hash in processed_hashes:
        return True, file_hash
    return False, file_hash


def move_file(source_path, destination_folder):
    # moving file from uploads to correct folder
    os.makedirs(destination_folder, exist_ok=True)

    file_name = os.path.basename(source_path)
    destination_path = os.path.join(
        destination_folder, file_name
    )

    # if file with same name exists add a number
    # so we dont accidentally overwrite anything
    counter = 1
    while os.path.exists(destination_path):
        name, ext = os.path.splitext(file_name)
        destination_path = os.path.join(
            destination_folder,
            f"{name}_{counter}{ext}"
        )
        counter += 1

    shutil.move(source_path, destination_path)
    return destination_path


def verify_move(destination_path):
    # double checking file actually got there
    # simple but important step
    return os.path.exists(destination_path)


def save_to_log(report):
    # saving report to log file
    # a means append so old records stay
    log_path = "logs/processing_log.txt"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(report)
        f.write("\n")


def process_file(file_path):
    # this is the main function
    # it runs all stages for one file
    # i designed it so each stage handles
    # its own failure case cleanly

    print("\n" + "=" * 50)
    print(f"processing: {os.path.basename(file_path)}")
    print("=" * 50)

    # recording start time to calculate how long it takes
    start_time = time.time()

    # basic file info i need for the report later
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    file_ext  = os.path.splitext(file_path)[1].lower()

    # stage 1 - validate the file
    # checking if file is usable before doing anything
    print("\nstage 1: validating...")
    validation = check_file(file_path)

    if validation["status"] == "rejected":
        print(f"rejected: {validation['reason']}")
        dest = move_file(
            file_path,
            "documents/miscellaneous/unreadable"
        )
        time_taken = round(time.time() - start_time, 2)
        report = generate_report(
            file_name, file_size, file_ext,
            "No", "No", "Rejected",
            "miscellaneous/unreadable",
            time_taken, "rejected"
        )
        save_to_log(report)
        return {"status": "rejected"}

    if validation["status"] == "warning":
        # large file warning but still processing
        print(f"warning: {validation['reason']}")

    print("validation passed ✅")

    # stage 2 - duplicate check
    # dont want to process same file twice
    print("\nstage 2: checking duplicate...")
    duplicate, file_hash = is_duplicate(file_path)

    if duplicate:
        print("this file was already processed before!")
        dest = move_file(file_path, "documents/duplicates")
        time_taken = round(time.time() - start_time, 2)
        report = generate_report(
            file_name, file_size, file_ext,
            "Yes", "No", "Duplicate",
            "documents/duplicates",
            time_taken, "duplicate"
        )
        save_to_log(report)
        return {"status": "duplicate", "destination": dest}

    print("not a duplicate ✅")

    # stage 3 - extract text from file
    # different approach for each file type
    print("\nstage 3: extracting text...")
    text = extract_text(file_path)

    # supported file types that should be readable
    # if these fail text extraction it means
    # file is empty or corrupted → unreadable
    SUPPORTED_EXTENSIONS = [
        ".pdf", ".docx", ".txt",
        ".jpg", ".jpeg", ".png",
        ".xlsx", ".pptx"
    ]

    if text is None or text.strip() == "":
        print("couldnt read this file")

        # if its a supported type that failed
        # → file is empty or corrupted → unreadable
        # if its an unsupported type
        # → we dont handle this format → unsupported
        if file_ext in SUPPORTED_EXTENSIONS:
            folder = "documents/miscellaneous/unreadable"
            move_status = "unreadable"
            print("supported type but empty/corrupted → unreadable")
        else:
            folder = "documents/miscellaneous/unsupported"
            move_status = "unsupported"
            print("unsupported file type → unsupported")

        dest = move_file(file_path, folder)
        time_taken = round(time.time() - start_time, 2)
        report = generate_report(
            file_name, file_size, file_ext,
            "No", "No", move_status.capitalize(),
            folder, time_taken, move_status
        )
        save_to_log(report)
        return {"status": move_status, "destination": dest}

    print(f"got {len(text)} characters ✅")

    # stage 4 - classify using my ml model
    print("\nstage 4: classifying...")

    # i added this check after realising pptx and xlsx
    # files were being wrongly classified as resumes
    # because they share some common words
    # better to send them to unknown than guess wrong
    NON_DOCUMENT_EXTENSIONS = [".pptx", ".xlsx"]

    if file_ext in NON_DOCUMENT_EXTENSIONS:
        print(f"{file_ext} is not a standard document")
        print("sending to unknown folder")
        dest = move_file(file_path, "documents/unknown")
        time_taken = round(time.time() - start_time, 2)
        report = generate_report(
            file_name, file_size, file_ext,
            "No", "Yes", "Unknown",
            "documents/unknown",
            time_taken, "non-document file type"
        )
        save_to_log(report)
        processed_hashes.add(file_hash)
        return {
            "status":        "success",
            "file_name":     file_name,
            "document_type": "Unknown",
            "confidence":    0.0,
            "destination":   dest,
            "method":        "file type check",
            "time_taken":    time_taken
        }

    if model is None:
        print("model not loaded - run train.py first")
        return {"status": "error"}

    result      = classify_document(text, model, vectorizer)
    doc_type    = result["document_type"]
    confidence  = result["confidence"]
    destination = result["destination"]
    method      = result["method"]

    print(f"type: {doc_type} ✅")
    print(f"confidence: {confidence}%")
    print(f"method: {method}")

    # stage 5 - move file to correct folder
    print("\nstage 5: moving file...")
    final_path = move_file(file_path, destination)
    print(f"moved to: {final_path} ✅")

    # stage 6 - verify file actually moved
    print("\nstage 6: verifying...")
    verified = verify_move(final_path)

    if verified:
        print("verified ✅")
        status = "success"
    else:
        print("verification failed ❌")
        status = "failed"

    # adding hash to processed set
    # so if same file comes again we catch it
    processed_hashes.add(file_hash)

    # stage 7 - generate report and save to log
    print("\nstage 7: saving report...")
    time_taken = round(time.time() - start_time, 2)

    report = generate_report(
        file_name, file_size, file_ext,
        "No", "Yes", doc_type,
        destination, time_taken, status
    )

    save_to_log(report)
    print(f"done in {time_taken} seconds ✅")

    return {
        "status":        status,
        "file_name":     file_name,
        "document_type": doc_type,
        "confidence":    confidence,
        "destination":   final_path,
        "method":        method,
        "time_taken":    time_taken
    }


def process_all_uploads():
    # processes every file sitting in uploads folder
    # useful for batch processing
    print("\nprocessing uploads folder...")

    # getting list of files only not folders
    files = [
        f for f in os.listdir("uploads")
        if os.path.isfile(os.path.join("uploads", f))
    ]

    if len(files) == 0:
        print("uploads folder is empty")
        print("add some files and try again")
        return []

    print(f"found {len(files)} files")

    results = []
    for file in files:
        file_path = os.path.join("uploads", file)
        result    = process_file(file_path)
        results.append(result)

    # showing summary at the end
    print("\n" + "=" * 50)
    print("summary")
    print("=" * 50)

    success = sum(1 for r in results
                  if r.get("status") == "success")
    failed  = len(results) - success

    print(f"total   : {len(results)}")
    print(f"success : {success}")
    print(f"failed  : {failed}")

    return results


if __name__ == "__main__":

    print("starting pipeline\n")

    # making sure all folders exist first
    create_folders()

    # process everything in uploads folder
    process_all_uploads()