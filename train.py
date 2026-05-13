import os
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# this file trains my ML model
# i learned about TF-IDF and logistic regression
# and tried to implement it here for document classification


def load_training_data():

    # each file has samples for one document type
    data_files = {
        "training_data/resumes.txt":   "Resume",
        "training_data/invoices.txt":  "Invoice",
        "training_data/paystubs.txt":  "Paystub",
        "training_data/contracts.txt": "Contract"
    }

    texts  = []
    labels = []

    for file_path, label in data_files.items():

        if not os.path.exists(file_path):
            print(f"could not find file: {file_path}")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        count = 0
        for line in lines:
            line = line.strip()
            # skip empty or very short lines
            if len(line) > 20:
                texts.append(line)
                labels.append(label)
                count += 1

        print(f"loaded {label}: {count} samples")

    return texts, labels


def train_model(texts, labels):

    print("\nstarting training...")

    # splitting data - 80% for learning 20% for testing
    # i read that this is a common approach in ML
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels,
        test_size=0.2,
        random_state=42
    )

    print(f"training on {len(X_train)} samples")
    print(f"testing on {len(X_test)} samples")

    # TF-IDF converts words to numbers
    # i tuned these settings after getting low confidence
    # ngram_range=(1,3) helped a lot with accuracy
    vectorizer = TfidfVectorizer(
        max_features=3000,
        ngram_range=(1, 3),
        stop_words="english",
        min_df=1,
        sublinear_tf=True
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf  = vectorizer.transform(X_test)

    # i chose logistic regression because it is simple
    # and gives confidence scores which i need for fallback
    # C=5 improved my confidence scores significantly
    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        C=5,
        solver='lbfgs'
    )

    model.fit(X_train_tfidf, y_train)
    print("model trained!")

    return model, vectorizer, X_test_tfidf, y_test


def test_model(model, X_test_tfidf, y_test):

    print("\nchecking accuracy...")

    predictions = model.predict(X_test_tfidf)
    accuracy = accuracy_score(y_test, predictions)

    print(f"accuracy: {accuracy * 100:.2f}%")
    print(classification_report(y_test, predictions))

    return accuracy


def save_model(model, vectorizer):

    # saving model so i dont have to retrain every time
    # pickle saves python objects to files
    with open("ml_model/model.pkl", "wb") as f:
        pickle.dump(model, f)

    with open("ml_model/vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)

    print("model saved to ml_model folder")


def test_with_examples(model, vectorizer):

    # i wrote these test cases myself
    # to check if model works on real looking text
    print("\ntesting with my own examples...")

    examples = [
        {
            # i found this type of text in a real resume
            "text": "My name is John Smith I have 5 years of experience as a software engineer I know Python and machine learning I completed my bachelor degree in computer science",
            "expected": "Resume"
        },
        {
            # testing with text that looks like a real invoice
            "text": "Please pay invoice number 1234 total amount is 500 dollars payment is due by April 30 this bill is for web development services provided to ABC company",
            "expected": "Invoice"
        },
        {
            # based on how salary slips actually look
            "text": "Employee salary for month of January gross pay is 5000 dollars federal tax deducted 800 dollars social security deducted 200 dollars net pay deposited 3900 dollars",
            "expected": "Paystub"
        },
        {
            # based on real agreement documents i have seen
            "text": "This agreement is made between company A and company B both parties agree to the terms and conditions mentioned below this contract is legally binding",
            "expected": "Contract"
        }
    ]

    all_correct = True

    for example in examples:

        text     = example["text"]
        expected = example["expected"]

        text_tfidf = vectorizer.transform([text])
        prediction = model.predict(text_tfidf)[0]

        # confidence score decides if we use ML or Ollama
        # below 70% means ollama will handle it instead
        probabilities = model.predict_proba(text_tfidf)[0]
        confidence    = max(probabilities) * 100

        correct = "✅" if prediction == expected else "❌"
        if prediction != expected:
            all_correct = False

        print(f"{correct} Expected  : {expected}")
        print(f"   Predicted : {prediction}")
        print(f"   Confidence: {confidence:.1f}%")
        print("-" * 50)

    if all_correct:
        print("\nall examples correct!")
    else:
        print("\nsome wrong - need more training data")


if __name__ == "__main__":

    print("starting ML training\n")

    texts, labels = load_training_data()
    print(f"\ntotal samples loaded: {len(texts)}")

    if len(texts) < 10:
        print("not enough data to train")
        exit()

    model, vectorizer, X_test, y_test = train_model(
        texts, labels
    )

    accuracy = test_model(model, X_test, y_test)

    save_model(model, vectorizer)

    test_with_examples(model, vectorizer)

    print("\ntraining done!")