import os
import abc
import spacy
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F


class NLPModel:
    def __init__(self):
        self.text_to_vector = {}

    @staticmethod
    def normalize_text_for_nlp(text: str) -> str:
        return text.lower().replace("_", " ").replace(",", " ").replace(".", " ")

    @abc.abstractmethod
    def get_vector(self, text):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_similarity_between_vectors(self, vector1, vector2):
        raise NotImplementedError()

    def get_cached_vector(self, text):
        if text not in self.text_to_vector:
            self.text_to_vector[text] = self.get_vector(text)
        return self.text_to_vector[text]

    def get_nlp_similarity(self, text1, text2):
        vector1 = self.get_cached_vector(text1)
        vector2 = self.get_cached_vector(text2)
        return self.get_similarity_between_vectors(vector1, vector2)


class EnglishNLPModel(NLPModel):
    def __init__(self):
        super().__init__()
        self.nlp = spacy.load("en_core_web_lg")  # python -m spacy download en_core_web_lg

    def get_vector(self, text):
        return self.nlp(self.normalize_text_for_nlp(text))

    def get_similarity_between_vectors(self, vector1, vector2):
        if not vector1.has_vector:
            return 0
        else:
            return vector1.similarity(vector2)


class HebrewNLPModel(NLPModel):
    def __init__(self):
        super().__init__()
        save_dir = os.path.expanduser(r"~/hebrew_model")
        os.makedirs(save_dir, exist_ok=True)

        model_name = "avichr/heBERT"
        files = ["config.json", "pytorch_model.bin", "vocab.txt"]

        for file_name in files:
            path = hf_hub_download(repo_id=model_name, filename=file_name, cache_dir=save_dir)
            print(f"Downloaded {file_name} to {path}")

        hebrew_model_dir = os.path.dirname(path)
        self.tokenizer = AutoTokenizer.from_pretrained(hebrew_model_dir)
        self.model = AutoModel.from_pretrained(hebrew_model_dir)

    def get_vector(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1)

    def get_similarity_between_vectors(self, vector1, vector2):
        return F.cosine_similarity(vector1, vector2).item()
