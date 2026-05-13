import pickle
import os

# i built this to classify documents using my trained model
# took me a while to understand how pickle loading works
# but basically i just load what i saved in train.py

# i set this after testing - below 70% the model
# was making mistakes so i added ollama as backup
CONFIDENCE_THRESHOLD = 70.0

# this maps each document type to its folder
# i designed it so adding new types is easy
# just add one line here
FOLDER_MAP = {
    "Resume":   "documents/hr/resumes",
    "Invoice":  "documents/finance/invoices",
    "Paystub":  "documents/finance/paystubs",
    "Contract": "documents/legal/contracts",
    "Unknown":  "documents/unknown"
}


def load_model():
    # loading both files i saved in train.py
    # i need both because vectorizer converts text
    # and model does the actual prediction
    # without vectorizer the model gets wrong numbers

    model_path      = "ml_model/model.pkl"
    vectorizer_path = "ml_model/vectorizer.pkl"

    # checking files exist before trying to load
    # learned this the hard way when i got errors
    if not os.path.exists(model_path):
        print("model not found - run train.py first")
        return None, None

    if not os.path.exists(vectorizer_path):
        print("vectorizer not found - run train.py first")
        return None, None

    # rb means read binary - models are saved as binary
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    with open(vectorizer_path, "rb") as f:
        vectorizer = pickle.load(f)

    print("model loaded!")
    return model, vectorizer


def classify_with_ml(text, model, vectorizer):
    # converting text to numbers first
    # has to be same vectorizer from training
    # otherwise numbers mean different things
    text_tfidf = vectorizer.transform([text])

    # getting prediction from model
    prediction = model.predict(text_tfidf)[0]

    # predict_proba gives probability for each category
    # i take the highest one as my confidence score
    probabilities = model.predict_proba(text_tfidf)[0]
    confidence    = max(probabilities) * 100

    return prediction, confidence


def classify_with_ollama(text):
    # i use ollama as backup when ml is not sure
    # ollama runs locally - no internet no api key
    # i already had it installed on my laptop

    try:
        import ollama

        # sending text to ollama with clear instructions
        # i tried different prompts and this one worked best
        response = ollama.chat(
            model="llama3",
            messages=[{
                "role": "user",
                "content": f"""You are a document classifier.
Read the document text below and classify it.
Reply with ONLY one word from these options:
Resume, Invoice, Paystub, Contract, Unknown

Document text:
{text[:1000]}

Reply with one word only:"""
            }]
        )

        result = response['message']['content'].strip()

        # making sure ollama gave me a valid answer
        # sometimes it adds extra words so i check carefully
        valid_categories = ["Resume", "Invoice",
                          "Paystub", "Contract", "Unknown"]

        for category in valid_categories:
            if category.lower() in result.lower():
                return category

        # if ollama gave something unexpected
        return "Unknown"

    except Exception as e:
        # ollama might not be running or model not downloaded
        print(f"ollama didnt work: {e}")
        return "Unknown"


def get_destination(document_type):
    # simple lookup to find the right folder
    # .get() with default means unknown types
    # go to unknown folder instead of crashing
    return FOLDER_MAP.get(document_type,
                          "documents/unknown")


def classify_document(text, model, vectorizer):
    # main function that pipeline.py will call
    # returns everything pipeline needs to know

    print("\nclassifying...")

    # first try with my ml model
    ml_prediction, confidence = classify_with_ml(
        text, model, vectorizer
    )

    print(f"ml says        : {ml_prediction}")
    print(f"ml confidence  : {confidence:.1f}%")

    # if confidence is good enough trust ml model
    if confidence >= CONFIDENCE_THRESHOLD:
        print("confidence is good - using ml result")
        final_prediction = ml_prediction
        method_used      = "ML Model"

    else:
        # ml not confident enough
        # ask ollama for help
        print("ml not confident - asking ollama...")
        ollama_prediction = classify_with_ollama(text)
        print(f"ollama says    : {ollama_prediction}")
        final_prediction  = ollama_prediction
        method_used       = "Ollama AI"

    # find destination folder for this document type
    destination = get_destination(final_prediction)

    # putting everything in a dictionary
    # so pipeline can easily access each piece
    result = {
        "document_type": final_prediction,
        "confidence":    round(confidence, 1),
        "destination":   destination,
        "method":        method_used
    }

    print(f"\nresult:")
    print(f"type        : {result['document_type']}")
    print(f"confidence  : {result['confidence']}%")
    print(f"destination : {result['destination']}")
    print(f"method      : {result['method']}")

    return result


if __name__ == "__main__":

    print("testing classifier\n")

    # loading model before anything else
    model, vectorizer = load_model()

    if model is None:
        print("could not load model")
        print("run train.py first")
        exit()

    # i wrote these test cases myself
    # based on real documents i have seen
    test_samples = [
        {
            "text": "My name is John Smith I have 5 years experience as software engineer I know Python machine learning completed bachelor degree computer science",
            "expected": "Resume"
        },
        {
            "text": "Please pay invoice number 1234 total amount 500 dollars payment due April 30 bill for web development services ABC company",
            "expected": "Invoice"
        },
        {
            "text": "Employee salary January gross pay 5000 dollars federal tax deducted 800 social security 200 net pay deposited 3900 dollars",
            "expected": "Paystub"
        },
        {
            "text": "This agreement made between company A and company B both parties agree terms conditions contract legally binding signed",
            "expected": "Contract"
        }
    ]

    print("=" * 50)
    correct = 0

    for sample in test_samples:
        result = classify_document(
            sample["text"],
            model,
            vectorizer
        )

        expected  = sample["expected"]
        predicted = result["document_type"]

        if predicted == expected:
            correct += 1
            status = "✅ correct"
        else:
            status = "❌ wrong"

        print(f"\n{status}")
        print(f"expected  : {expected}")
        print(f"predicted : {predicted}")
        print("=" * 50)

    print(f"\nscore: {correct}/4 correct")