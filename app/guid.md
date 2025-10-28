# 🔨 BACKEND IMPLEMENTATION GUIDE

Guide chi tiết để implement từng task trong checklist của bạn.

---

## 📦 PART 1: EMBEDDING & VECTOR DATABASE

### Task 1: Setup Pinecone ✅
**Time:** 30 minutes

```python
# scripts/setup_pinecone.py
from pinecone import Pinecone, ServerlessSpec
import time

PINECONE_API_KEY = "pcsk_xxxxx"  # Get from pinecone.io
INDEX_NAME = "products"
DIMENSION = 384  # For multilingual-MiniLM

pc = Pinecone(api_key=PINECONE_API_KEY)

# Create index
pc.create_index(
    name=INDEX_NAME,
    dimension=DIMENSION,
    metric="cosine",
    spec=ServerlessSpec(cloud='aws', region='us-east-1')
)

print("✅ Pinecone index created!")
```

---

### Task 2: Generate embeddings ✅
**Time:** 1-2 hours

**Complete script:** `scripts/generate_embeddings_local.py`

```python
"""
Generate embeddings for ALL products - LOCAL MODEL (FREE)
"""
import psycopg2
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from tqdm import tqdm

# Config
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "your_password",
    "dbname": "shopping_chatbot"
}

PINECONE_API_KEY = "your-key"
PINECONE_INDEX = "products"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE = 100

# 1. Load model
print("🧠 Loading model...")
model = SentenceTransformer(EMBEDDING_MODEL)
print(f"✅ Dimension: {model.get_sentence_embedding_dimension()}")

# 2. Connect to Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

# 3. Fetch products
print("\n📊 Fetching products...")
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        p.product_id, p.product_name, p.product_description,
        p.original_price, p.discount_price,
        p.category1, p.category2, p.category3,
        p.status, p.count,
        s.shop_id, s.shop_name
    FROM products p
    JOIN shops s ON p.shop_id = s.shop_id
    WHERE p.status = 'available'
""")

products = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
cursor.close()
conn.close()

print(f"✅ Fetched {len(products)} products")

# 4. Process in batches
print(f"\n🔄 Generating embeddings...")
total_uploaded = 0

for i in tqdm(range(0, len(products), BATCH_SIZE)):
    batch = products[i:i + BATCH_SIZE]
    
    # Create embedding texts
    texts = []
    for row in batch:
        product = dict(zip(columns, row))
        text = f"{product['product_name']} | Shop: {product['shop_name']}"
        if product['category1']:
            text += f" | {product['category1']}"
        texts.append(text)
    
    # Generate embeddings
    embeddings = model.encode(texts, normalize_embeddings=True)
    
    # Prepare vectors
    vectors = []
    for j, row in enumerate(batch):
        product = dict(zip(columns, row))
        vectors.append((
            product['product_id'],
            embeddings[j].tolist(),
            {
                'product_name': product['product_name'],
                'shop_name': product['shop_name'],
                'category1': product['category1'] or '',
                'discount_price': float(product['discount_price']),
                'status': product['status']
            }
        ))
    
    # Upload to Pinecone
    index.upsert(vectors=vectors, namespace='products')
    total_uploaded += len(vectors)

print(f"\n✅ Uploaded {total_uploaded} products to Pinecone!")

# 5. Test search
print("\n🧪 Testing search...")
test_query = "iPhone 15"
test_emb = model.encode(test_query, normalize_embeddings=True)
results = index.query(
    vector=test_emb.tolist(),
    top_k=3,
    include_metadata=True,
    namespace='products'
)

print(f"Query: '{test_query}'")
for match in results['matches']:
    print(f"  - {match['metadata']['product_name']} (score: {match['score']:.3f})")

print("\n✅ ALL DONE!")
```

**Run:**
```bash
pip install sentence-transformers pinecone-client psycopg2-binary tqdm
python scripts/generate_embeddings_local.py
```

---

## 🔴 PART 2: REDIS SESSION MANAGEMENT

### Task 3: Setup Redis ✅
**Time:** 15 minutes

```yaml
# docker-compose.redis.yml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

```bash
docker-compose -f docker-compose.redis.yml up -d
docker exec -it <container> redis-cli ping  # Should return PONG
```

---

### Task 4: Session Manager ✅
**Time:** 2 hours

**File:** `app/utils/session_manager.py`

```python
"""Redis Session Manager"""
import redis
import json
from datetime import datetime
from typing import Optional, Dict
import uuid

class SessionManager:
    def __init__(self, redis_url="redis://localhost:6379/0", ttl=1800):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl  # 30 minutes
    
    def create_session(self, user_id: str, session_id: str = None) -> Dict:
        """Create new session"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
            "context": {}
        }
        
        self.redis.setex(
            f"session:{session_id}",
            self.ttl,
            json.dumps(data)
        )
        return data
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        key = f"session:{session_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add message to session"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep last 50 messages
        if len(session["messages"]) > 50:
            session["messages"] = session["messages"][-50:]
        
        self.redis.setex(
            f"session:{session_id}",
            self.ttl,
            json.dumps(session)
        )
    
    def extend_ttl(self, session_id: str):
        """Extend session TTL"""
        self.redis.expire(f"session:{session_id}", self.ttl)

# Test
if __name__ == "__main__":
    manager = SessionManager()
    
    # Create session
    session = manager.create_session(user_id="user_123")
    print(f"✅ Session created: {session['session_id']}")
    
    # Add messages
    manager.add_message(session['session_id'], "user", "Hello")
    manager.add_message(session['session_id'], "assistant", "Hi!")
    
    # Get session
    retrieved = manager.get_session(session['session_id'])
    print(f"✅ Messages: {len(retrieved['messages'])}")
```

---

## 📨 PART 3: KAFKA MESSAGE QUEUE

### Task 5: Setup Kafka ✅
**Time:** 1 hour

```yaml
# docker-compose.kafka.yml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

```bash
docker-compose -f docker-compose.kafka.yml up -d
```

---

### Task 6: Kafka Producer ✅
**Time:** 1 hour

```python
# app/kafka/producer.py
from kafka import KafkaProducer
import json

class ChatProducer:
    def __init__(self, bootstrap_servers="localhost:9092"):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
    
    def send_chat_request(self, data: dict):
        """Send to chat-requests topic"""
        self.producer.send('chat-requests', value=data)
        self.producer.flush()
        print(f"✅ Sent: {data['message_id']}")

# Usage
producer = ChatProducer()
producer.send_chat_request({
    "message_id": "msg_123",
    "session_id": "sess_456",
    "user_id": "user_789",
    "message": "Tìm iPhone 15"
})
```

---

### Task 7: Kafka Consumer ✅
**Time:** 2 hours

```python
# app/kafka/consumer.py
from kafka import KafkaConsumer
import json

class ChatConsumer:
    def __init__(self, bootstrap_servers="localhost:9092"):
        self.consumer = KafkaConsumer(
            'chat-requests',
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='ai-service-group'
        )
    
    def process_messages(self, callback):
        """Process messages with callback function"""
        print("🔄 Listening for messages...")
        for message in self.consumer:
            data = message.value
            print(f"📨 Received: {data['message_id']}")
            
            # Process with callback
            result = callback(data)
            
            # TODO: Send result to chat-responses topic
            print(f"✅ Processed: {data['message_id']}")

# Usage
def process_chat(data):
    # Your AI processing here
    print(f"   Message: {data['message']}")
    return {"response": "OK"}

consumer = ChatConsumer()
consumer.process_messages(process_chat)
```

---

## 🚪 PART 4: API GATEWAY

### Task 8: Kong Gateway ✅
**Time:** 2 hours

```yaml
# docker-compose.kong.yml
version: '3.8'
services:
  kong-database:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: kong
      POSTGRES_DB: kong
      POSTGRES_PASSWORD: kong
    ports:
      - "5433:5432"

  kong:
    image: kong:3.4
    depends_on:
      - kong-database
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-database
      KONG_PG_USER: kong
      KONG_PG_PASSWORD: kong
      KONG_PROXY_LISTEN: 0.0.0.0:8000
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
    ports:
      - "8000:8000"  # Proxy
      - "8001:8001"  # Admin API
```

```bash
docker-compose -f docker-compose.kong.yml up -d
```

---

### Task 9: Kong Routes & Plugins ✅
**Time:** 1 hour

```bash
# Create service
curl -X POST http://localhost:8001/services \
  --data name=chat-api \
  --data url=http://host.docker.internal:8000

# Create route
curl -X POST http://localhost:8001/services/chat-api/routes \
  --data paths[]=/api/chat

# Add rate limiting
curl -X POST http://localhost:8001/services/chat-api/plugins \
  --data name=rate-limiting \
  --data config.minute=10

# Test
curl http://localhost:8000/api/chat
```

---

## 🐍 PART 5: FASTAPI BACKEND

### Task 10: FastAPI Chat API ✅
**Time:** 3 hours

```python
# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI(title="AI Shopping Chatbot")

# Models
class ChatRequest(BaseModel):
    session_id: str = None
    user_id: str
    message: str

class ChatResponse(BaseModel):
    message_id: str
    session_id: str
    status: str
    message: str

# Endpoint
@app.post("/api/v1/chat/message")
async def send_message(request: ChatRequest):
    """Send chat message"""
    
    message_id = str(uuid.uuid4())
    session_id = request.session_id or str(uuid.uuid4())
    
    # TODO: 
    # 1. Get/create session in Redis
    # 2. Add user message to session
    # 3. Publish to Kafka
    
    return ChatResponse(
        message_id=message_id,
        session_id=session_id,
        status="processing",
        message="Message received"
    )

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Run: uvicorn app.main:app --reload
```

---

## 🎯 QUICK START COMMANDS

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start infrastructure
docker-compose up -d  # Redis + Kafka + Kong

# 3. Generate embeddings
python scripts/generate_embeddings_local.py

# 4. Start FastAPI
uvicorn app.main:app --reload --port 8000

# 5. Test
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "message": "Hello"}'
```

---

## 📦 requirements.txt

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Database
psycopg2-binary==2.9.9
redis==5.0.1

# Kafka
kafka-python==2.0.2

# Vector/Embeddings
pinecone-client==3.0.0
sentence-transformers==2.2.2

# Utils
python-dotenv==1.0.0
tqdm==4.66.1
```

---

## ✅ TESTING CHECKLIST

- [ ] Pinecone index created và có data
- [ ] Redis connection works
- [ ] Session create/get/update works
- [ ] Kafka producer sends messages
- [ ] Kafka consumer receives messages
- [ ] Kong proxy works
- [ ] FastAPI endpoint responds
- [ ] End-to-end test: FE → Kong → API → Kafka → Response

---

Bạn muốn tôi viết thêm phần nào? Integration tests? Docker compose tổng hợp? 🚀