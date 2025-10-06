from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_chroma import Chroma
import gradio as gr
from dotenv import load_dotenv
import pandas as pd
import numpy as np

load_dotenv()

books = pd.read_csv('books_with_emotions.csv')
books['large_thumbnail'] = books['thumbnail'] + '&fife=w800'
books['large_thumbnail'] = np.where(
    books['large_thumbnail'].isna(),
    'cover_photo_not_found.png',
    books['large_thumbnail']
)

# Load text
raw_text = TextLoader("tagged_description.txt", encoding="utf-8").load()
# Split text
txt_splitter = CharacterTextSplitter(separator="\n", chunk_size=500, chunk_overlap=50)
documents = txt_splitter.split_documents(raw_text)
db_books = Chroma.from_documents(documents, HuggingFaceEmbeddings())

def retrive_semantic_recommender(
        query: str,
        category: str = None,
        tone: str = None,
        initial_top_k: int = 50,
        final_top_k: int = 16,
) -> pd.DataFrame:
    recs = db_books.similarity_search_with_score(query, initial_top_k)

    # Clean ISBN numbers
    book_list = [
        int(rec[0].page_content.strip('"').split()[0].replace(":",""))
        for rec in recs
    ]

    book_recs = books[books['isbn13'].isin(book_list)].head(final_top_k)

    if category != 'All':
        book_recs = book_recs[book_recs['simple_categories'] == category].head(final_top_k)

    if tone == 'Happy':
        book_recs = book_recs.sort_values(by='joy', ascending=False).head(final_top_k)
    elif tone == 'Surprising':
        book_recs = book_recs.sort_values(by='surprise', ascending=False).head(final_top_k)
    elif tone == 'Angry':
        book_recs = book_recs.sort_values(by='anger', ascending=False).head(final_top_k)
    elif tone == 'Suspenseful':
        book_recs = book_recs.sort_values(by='fear', ascending=False).head(final_top_k)
    elif tone == 'Sad':
        book_recs = book_recs.sort_values(by='sadness', ascending=False).head(final_top_k)

    return book_recs

def recommend_book(query: str, category: str, tone: str):
    recommendations = retrive_semantic_recommender(query, category, tone)
    results = []

    for _, row in recommendations.iterrows():
        description = row["description"]
        truncated_desc_split = description.split()
        truncated_description = ' '.join(truncated_desc_split[:30]) + '...'

        author_split = row["authors"].split(':')
        if len(author_split) == 2:
            authors_str = f"{', '.join(author_split[:-1])}, and {author_split[-1]}"
        else:
            authors_str = row['authors']

        caption = f"{row['title']} by {authors_str}: {truncated_description}"
        results.append((row["large_thumbnail"], caption))

    return results

categories = ["All"] + sorted(books['simple_categories'].unique())
tones = ["All", "Happy", "Surprising", "Angry", "Suspenseful", "Sad"]

with gr.Blocks(theme=gr.themes.Glass()) as dashboard:
    gr.Markdown("# 📚 Semantic Book Recommender")

    with gr.Row():
        user_query = gr.Textbox(label="Please enter a description of a book:",
                                placeholder="e.g. A story about forgiveness")

        category_dropdown = gr.Dropdown(choices=categories, label="Select a category:", value="All")
        tone_dropdown = gr.Dropdown(choices=tones, label="Select an emotional tone:", value="All")

    gr.Markdown("## 📖 Recommendations")
    output = gr.Gallery(label="Recommended books", columns=4, rows=2)

    submit_button = gr.Button("Recommend")
    submit_button.click(fn=recommend_book,
                        inputs=[user_query, category_dropdown, tone_dropdown],
                        outputs=output)

if __name__ == "__main__":
    dashboard.launch()
