import pandas as pd
from gensim import corpora
from gensim.models import LdaModel
from nltk.tokenize import SpaceTokenizer
import pyLDAvis
import pyLDAvis.gensim_models
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import re
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import time
import matplotlib
matplotlib.use('Agg')  # Tkinter 기반 백엔드 사용 방지
import requests
#####################################################
# ***** JAVA 안쓰고 *****
#####################################################

class TopicModeling:
    def __init__(self, csv_file, num_topics=5, output_dir="topic_img", extra_stopwords=None):
        self.df = pd.read_csv(csv_file)
        self.num_topics = num_topics
        self.texts = []
        self.dictionary = None
        self.corpus = None
        self.lda_model = None
        self.output_dir = output_dir
        self.space_tokenizer = SpaceTokenizer()
        self.stopwords = self.load_stopwords_from_github()
        # ✅ 사용자 정의 불용어 추가
        if extra_stopwords:
            self.stopwords.update(extra_stopwords)
            print(f"✅ 사용자 불용어 {len(extra_stopwords)}개 추가됨")

        os.makedirs(self.output_dir, exist_ok=True)

    def load_stopwords_from_github(self):
        """
        GitHub에서 한국어 불용어 리스트를 로드
        """
        url = "https://raw.githubusercontent.com/stopwords-iso/stopwords-ko/master/stopwords-ko.txt"
        try:
            response = requests.get(url)
            response.raise_for_status()
            stopwords = set(line.strip() for line in response.text.splitlines() if line.strip())
            print(f"✅ 불용어 {len(stopwords)}개 로드 완료")
            return stopwords
        except Exception as e:
            print("❌ 불용어 로드 실패:", e)
            return set()

    def preprocess_texts(self):
        for text in self.df['INFO']:
            tokens = self.space_tokenizer.tokenize(str(text))
            filtered_tokens = [
                word for word in tokens
                if word.isalpha() and word not in self.stopwords
            ]
            self.texts.append(filtered_tokens)

    def create_dictionary_and_corpus(self):
        self.dictionary = corpora.Dictionary(self.texts)
        self.corpus = [self.dictionary.doc2bow(text) for text in self.texts]

    def train_lda_model(self):
        self.lda_model = LdaModel(self.corpus, num_topics=self.num_topics, id2word=self.dictionary, passes=15)
        for idx, topic in self.lda_model.print_topics(-1):
            print(f"Topic {idx}: {topic}")

    def extract_korean_words(self):
        korean_words_dict = {}
        for i in range(self.num_topics):
            topic_words = self.lda_model.show_topic(i, topn=30)
            korean_words = [word for word, prob in topic_words if re.match(r'^[\uAC00-\uD7A3]+$', word)]
            korean_words_dict[i] = korean_words
            print(f"Topic {i}: {', '.join(korean_words)}")
        return korean_words_dict

    def create_korean_wordcloud(self):
        for i in range(self.num_topics):
            plt.figure(figsize=(10, 5))
            plt.title(f'Topic {i+1}')
            words = self.lda_model.show_topic(i, topn=30)
            word_freq = defaultdict(float)
            for word, prob in words:
                if re.match(r'^[\uAC00-\uD7A3]+$', word):
                    word_freq[word] += prob

            wordcloud = WordCloud(
                width=800, height=400, background_color='black',
                font_path=r'C:/Windows/Fonts/malgun.ttf'
            ).generate_from_frequencies(word_freq)

            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.tight_layout()
            filepath = os.path.join(self.output_dir, f"wordcloud_topic_{i+1}.png")
            plt.savefig(filepath)
            plt.close()
            print(f"✅ 워드클라우드 저장 완료: {filepath}")

    def visualize_lda_model(self):
        vis = pyLDAvis.gensim_models.prepare(self.lda_model, self.corpus, self.dictionary)
        html_path = os.path.join(self.output_dir, "lda_visualization.html")
        pyLDAvis.save_html(vis, html_path)

        # PNG 저장 (Selenium 사용)
        png_path = os.path.join(self.output_dir, "lda_visualization.png")
        options = Options()
        options.headless = True
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(1200, 900)
        driver.get("file://" + os.path.abspath(html_path))
        time.sleep(2)
        driver.save_screenshot(png_path)
        driver.quit()
        print(f"✅ pyLDAvis PNG 저장 완료: {png_path}")

    def run(self):
        self.preprocess_texts()
        self.create_dictionary_and_corpus()
        self.train_lda_model()
        self.extract_korean_words()
        self.create_korean_wordcloud()
        self.visualize_lda_model()