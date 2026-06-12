import os
import sys
from pathlib import Path

# Add backend directory to python path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.knowledge_service import get_embedding_model

def parse_markdown(text_content: str) -> list[tuple[str, str]]:
    """
    Parses a markdown file and splits it into sections by header.
    Returns a list of tuples: (section_title, section_content)
    """
    lines = text_content.split("\n")
    sections = []
    current_title = "General"
    current_content = []
    
    for line in lines:
        if line.startswith("#"):
            content_str = "\n".join(current_content).strip()
            if content_str:
                sections.append((current_title, content_str))
            
            # Extract header level and text
            header_text = line.lstrip("#").strip()
            current_title = header_text
            current_content = []
        else:
            current_content.append(line)
            
    content_str = "\n".join(current_content).strip()
    if content_str:
        sections.append((current_title, content_str))
        
    return sections

def seed_knowledge_base():
    kb_dir = Path("c:/Users/Aditi/OneDrive/Desktop/Dummy-SenAI/Dummy-SenAI/knowledge_base")
    if not kb_dir.exists():
        print(f"Error: Knowledge base directory {kb_dir} does not exist.")
        return

    print("Loading SentenceTransformer embedding model...")
    model = get_embedding_model()

    db = SessionLocal()
    try:
        # 1. Clean existing knowledge chunks
        print("Cleaning existing knowledge base chunks...")
        db.execute(text("DELETE FROM knowledge_chunks;"))
        db.commit()

        # 2. Iterate over all markdown files
        md_files = list(kb_dir.glob("*.md"))
        print(f"Found {len(md_files)} policy files to parse.")

        total_inserted = 0
        for md_file in md_files:
            source_doc = md_file.name
            print(f"Processing {source_doc}...")
            
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            sections = parse_markdown(content)
            print(f" - Parsed {len(sections)} sections.")
            
            for idx, (section_title, section_content) in enumerate(sections):
                # The pipeline embeds: f"{doc['section']}\n{doc['content']}"
                embed_text = f"{section_title}\n{section_content}"
                embedding_vector = model.encode(embed_text).tolist()
                
                vector_str = f"[{','.join(map(str, embedding_vector))}]"
                token_count = len(embed_text.split()) # Simple word count approximation
                
                db.execute(
                    text(
                        """
                        INSERT INTO knowledge_chunks (
                            source_doc,
                            chunk_index,
                            chunk_text,
                            embedding,
                            token_count,
                            metadata
                        ) VALUES (
                            :source_doc,
                            :chunk_index,
                            :chunk_text,
                            CAST(:embedding AS vector),
                            :token_count,
                            CAST(:metadata AS jsonb)
                        )
                        """
                    ),
                    {
                        "source_doc": source_doc,
                        "chunk_index": idx,
                        "chunk_text": section_content,
                        "embedding": vector_str,
                        "token_count": token_count,
                        "metadata": f'{{"section": "{section_title}"}}'
                    }
                )
                total_inserted += 1
                
        db.commit()
        print(f"Successfully seeded {total_inserted} chunks into the database!")
        
    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_knowledge_base()
