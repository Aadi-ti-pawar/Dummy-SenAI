"""
SenAI RAG Pipeline
Loads policy documents, generates embeddings, and stores in pgvector
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_batch
from sentence_transformers import SentenceTransformer
from datetime import datetime
import glob
from backend.config import settings

# Database config
DB_CONFIG = settings.db_config

# Embedding model (384-dim)
MODEL = SentenceTransformer(settings.embedding_model)

# Policy documents directory
POLICIES_DIR = str(settings.policies_dir)


def load_documents(policies_dir):
    """Load all markdown documents from policies directory"""
    print(f"\n📖 Loading policy documents from {policies_dir}...")
    
    documents = []
    md_files = glob.glob(os.path.join(policies_dir, '*.md'))
    
    if not md_files:
        print(f"❌ No .md files found in {policies_dir}")
        return []
    
    for md_file in md_files:
        filename = os.path.basename(md_file)
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by sections (##)
            sections = content.split('\n## ')
            
            for i, section in enumerate(sections):
                section_lines = section.split('\n')
                section_title = section_lines[0] if section_lines else 'Unknown'
                section_content = '\n'.join(section_lines[1:]).strip()
                
                if section_content:
                    documents.append({
                        'filename': filename,
                        'section': section_title,
                        'content': section_content[:2000]  # Limit to 2000 chars per section
                    })
            
            print(f"✓ Loaded {filename} ({len(sections)-1} sections)")
        
        except Exception as e:
            print(f"✗ Error loading {filename}: {e}")
    
    return documents


def generate_embeddings(documents):
    """Generate 384-dim embeddings for each document section"""
    print(f"\n🧠 Generating embeddings for {len(documents)} sections...")
    
    embeddings_data = []
    
    for i, doc in enumerate(documents):
        try:
            # Combine section title + content for embedding
            text = f"{doc['section']}\n{doc['content']}"
            
            # Generate embedding (returns numpy array)
            embedding = MODEL.encode(text)
            
            embeddings_data.append({
                'filename': doc['filename'],
                'section': doc['section'],
                'content': doc['content'],
                'embedding': embedding.tolist()  # Convert to list for storage
            })
            
            if (i + 1) % 5 == 0:
                print(f"  ✓ Generated {i+1}/{len(documents)} embeddings")
        
        except Exception as e:
            print(f"  ✗ Error embedding {doc['filename']} section {doc['section']}: {e}")
    
    print(f"✓ Generated {len(embeddings_data)} embeddings")
    return embeddings_data


def insert_embeddings_to_db(embeddings_data):
    """Insert embeddings into knowledge_chunks table"""
    print(f"\n💾 Inserting embeddings into database...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Prepare data for batch insert
        batch_data = []
        for index, item in enumerate(embeddings_data):
            batch_data.append((
                item['filename'],                              # source_doc
                index,                                         # chunk_index
                item['content'],                               # chunk_text
                f"[{','.join(map(str, item['embedding']))}]",  # embedding (pgvector format)
                len(item['content'].split()),                  # token_count approximation
                json.dumps({'section': item['section']}),       # metadata
                datetime.now()                                 # created_at
            ))
        
        # Batch insert
        insert_sql = """
        INSERT INTO knowledge_chunks (
            source_doc, chunk_index, chunk_text, embedding,
            token_count, metadata, created_at
        ) VALUES (%s, %s, %s, %s::vector, %s, %s::jsonb, %s)
        ON CONFLICT DO NOTHING
        """
        
        execute_batch(cur, insert_sql, batch_data, page_size=100)
        conn.commit()
        
        print(f"✓ Inserted {len(batch_data)} knowledge chunks into database")
        
        # Verify insertion
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        total_count = cur.fetchone()[0]
        print(f"✓ Total knowledge chunks in DB: {total_count}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Database insertion failed: {e}")
        raise


def vector_search_example():
    """Example: Search knowledge base with vector similarity"""
    print(f"\n🔍 Testing vector search with examples...")
    
    test_queries = [
        "What is the refund policy?",
        "How much does the enterprise plan cost?",
        "What is the uptime SLA?",
        "How do I submit a GDPR data request?"
    ]
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for query in test_queries:
            # Generate embedding for query
            query_embedding = MODEL.encode(query).tolist()
            
            # Search with vector similarity (cosine distance)
            search_sql = """
            SELECT source_doc,
                   COALESCE(metadata->>'section', source_doc) AS section,
                   chunk_text,
                   1 - (embedding <=> %s::vector) as similarity
            FROM knowledge_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT 3
            """
            
            cur.execute(search_sql, (
                f"[{','.join(map(str, query_embedding))}]",
                f"[{','.join(map(str, query_embedding))}]"
            ))
            
            results = cur.fetchall()
            
            print(f"\n  Query: '{query}'")
            for i, row in enumerate(results, 1):
                doc, section, content, similarity = row
                print(f"    {i}. [{doc}] {section} (similarity: {similarity:.3f})")
                print(f"       {content[:100]}...")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Vector search error: {e}")


def print_summary():
    """Print summary statistics"""
    print("\n" + "="*60)
    print("RAG PIPELINE SUMMARY")
    print("="*60)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Count chunks by document
        cur.execute("""
            SELECT source_doc, COUNT(*) as count
            FROM knowledge_chunks
            GROUP BY source_doc
            ORDER BY count DESC
        """)
        
        print("\n✓ Knowledge Chunks by Document:")
        for doc, count in cur.fetchall():
            print(f"  • {doc}: {count} chunks")
        
        # Total summary
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        total = cur.fetchone()[0]
        print(f"\n✓ Total knowledge chunks: {total}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error getting summary: {e}")
    
    print("="*60)


def main():
    """Main pipeline execution"""
    print("\n" + "="*60)
    print("SenAI RAG Pipeline - Load Policies into Vector DB")
    print("="*60)
    
    try:
        # Step 1: Load documents
        documents = load_documents(POLICIES_DIR)
        if not documents:
            print("❌ No documents loaded. Exiting.")
            return
        
        # Step 2: Generate embeddings
        embeddings_data = generate_embeddings(documents)
        if not embeddings_data:
            print("❌ No embeddings generated. Exiting.")
            return
        
        # Step 3: Insert into database
        insert_embeddings_to_db(embeddings_data)
        
        # Step 4: Test vector search
        vector_search_example()
        
        # Step 5: Print summary
        print_summary()
        
        print("\n✅ RAG PIPELINE COMPLETE!")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
