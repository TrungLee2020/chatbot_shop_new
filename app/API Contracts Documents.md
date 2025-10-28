# API Contracts & Data Structures Documentation

## AI Shopping Chatbot - Inter-Layer Communication

Tài liệu này mô tả **chi tiết các trường dữ liệu** giao tiếp giữa các layers trong hệ thống.

---

## 1. FRONTEND ↔ API GATEWAY

### 1.1. WebSocket Connection (Initial)

```json
// Event: connect
{
  "transport": "websocket",
  "headers": {
    "Authorization": "Bearer <JWT_TOKEN>",
    "X-Client-Version": "1.0.0",
    "X-Device-Type": "web|ios|android"
  }
}
```

### 1.2. Send Chat Message (FE → Gateway)

```json
// Event: chat:message
{
  "session_id": "string (UUID v4)",           // Required - Session identifier
  "user_id": "string",                        // Required - User identifier
  "message": "string",                        // Required - User message text
  "message_type": "text|voice|image",         // Optional - Default: "text"
  "timestamp": "string (ISO 8601)",           // Required - Client timestamp
  "client_info": {                            // Optional
    "platform": "web|ios|android",
    "version": "string",
    "user_agent": "string"
  },
  "context": {                                // Optional - Additional context
    "current_page": "string",                 // Current page URL
    "referrer": "string",                     // Referrer URL
    "utm_params": {}                          // UTM parameters
  }
}
```

**Validation Rules:**
- `session_id`: UUID v4 format, max 36 chars
- `user_id`: Max 50 chars, alphanumeric + underscore
- `message`: Min 1 char, max 1000 chars
- `timestamp`: ISO 8601 format

### 1.3. Receive Chat Response (Gateway → FE)

```json
// Event: chat:response
{
  "message_id": "string (UUID v4)",           // Unique message identifier
  "session_id": "string (UUID v4)",           // Session identifier
  "message": "string",                        // AI response text
  "message_type": "text|product_list|order_confirmation|error",
  "timestamp": "string (ISO 8601)",           // Server timestamp
  "products": [                               // Optional - Product recommendations
    {
      "product_id": "string",
      "product_name": "string",
      "product_url": "string",
      "original_price": "number",
      "discount_price": "number",
      "currency": "VND|USD",
      "images": ["string"],                   // Array of image URLs
      "shop": {
        "shop_id": "string",
        "shop_name": "string",
        "shop_url": "string"
      },
      "category1": "string",
      "category2": "string",
      "category3": "string",
      "status": "available|out_of_stock",
      "count": "number",                      // Stock quantity
      "rating": "number",                     // 0-5
      "review_count": "number"
    }
  ],
  "quick_actions": [                          // Optional - Quick reply buttons
    {
      "label": "string",
      "action": "view_details|add_to_cart|compare|buy_now",
      "payload": {}                           // Action-specific data
    }
  ],
  "intent": "string",                         // Detected intent
  "confidence": "number",                     // 0-1
  "suggestions": ["string"]                   // Follow-up suggestions
}
```

### 1.4. Error Response (Gateway → FE)

```json
// Event: chat:error
{
  "error_code": "string",                     // ERROR_CODE enum
  "message": "string",                        // User-friendly error message
  "timestamp": "string (ISO 8601)",
  "details": {                                // Optional debug info
    "request_id": "string",
    "trace_id": "string"
  }
}
```

**Error Codes:**
- `RATE_LIMIT_EXCEEDED`: Rate limit reached
- `INVALID_SESSION`: Invalid session_id
- `UNAUTHORIZED`: Authentication failed
- `SERVICE_UNAVAILABLE`: Backend service down
- `INVALID_REQUEST`: Malformed request

### 1.5. Typing Indicator (FE → Gateway)

```json
// Event: chat:typing
{
  "session_id": "string (UUID v4)",
  "user_id": "string",
  "is_typing": "boolean"
}
```

### 1.6. Session Status (Gateway → FE)

```json
// Event: session:status
{
  "session_id": "string (UUID v4)",
  "status": "active|expired|invalid",
  "expires_at": "string (ISO 8601)",          // Session expiry time
  "message_count": "number",                  // Messages in this session
  "remaining_quota": "number"                 // Remaining messages today
}
```

---

## 2. API GATEWAY ↔ CHAT API SERVICE

### 2.1. HTTP Request (Gateway → Chat API)

**Endpoint:** `POST /api/v1/chat/message`

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <JWT_TOKEN>",
  "X-Request-ID": "string (UUID)",           // Request trace ID
  "X-User-ID": "string",                     // Extracted from JWT
  "X-Gateway-Timestamp": "string (ISO 8601)",
  "X-Real-IP": "string"                      // Client IP address
}
```

**Body:**
```json
{
  "session_id": "string (UUID v4)",
  "user_id": "string",
  "message": "string",
  "message_type": "text|voice|image",
  "timestamp": "string (ISO 8601)",
  "client_info": {
    "platform": "string",
    "version": "string",
    "user_agent": "string"
  },
  "context": {}
}
```

### 2.2. HTTP Response (Chat API → Gateway)

**Success Response (202 Accepted):**
```json
{
  "status": "processing",
  "message_id": "string (UUID v4)",
  "session_id": "string (UUID v4)",
  "estimated_response_time": "number",        // Milliseconds
  "message": "Message received and being processed"
}
```

**Error Response (4xx/5xx):**
```json
{
  "status": "error",
  "error_code": "string",
  "message": "string",
  "timestamp": "string (ISO 8601)",
  "request_id": "string",
  "details": {}
}
```

---

## 3. CHAT API SERVICE ↔ REDIS

### 3.1. Session Key Structure

**Key Pattern:** `session:{session_id}`

**Example:** `session:550e8400-e29b-41d4-a716-446655440000`

**Value (JSON String):**
```json
{
  "user_id": "string",
  "created_at": "string (ISO 8601)",
  "last_activity": "string (ISO 8601)",
  "message_count": "number",                  // Total messages in session
  "messages": [                               // Last 50 messages
    {
      "message_id": "string (UUID v4)",
      "role": "user|assistant",
      "content": "string",
      "timestamp": "string (ISO 8601)",
      "products": [],                         // Only for assistant messages
      "intent": "string"                      // Only for assistant messages
    }
  ],
  "context": {
    "product_preferences": ["string"],        // Product categories
    "brands": ["string"],                     // Preferred brands
    "price_range": {
      "min": "number",
      "max": "number",
      "currency": "VND|USD"
    },
    "last_search": "string",                  // Last search query
    "last_viewed_products": ["string"],       // Product IDs
    "cart_items": ["string"],                 // Product IDs in cart
    "purchase_history": [                     // Past purchases
      {
        "product_id": "string",
        "purchase_date": "string (ISO 8601)",
        "price": "number"
      }
    ],
    "conversation_topics": ["string"],        // Detected topics
    "user_sentiment": "positive|neutral|negative",
    "engagement_score": "number"              // 0-100
  },
  "metadata": {
    "platform": "string",
    "device_type": "string",
    "location": "string",
    "language": "vi|en",
    "timezone": "string"
  }
}
```

**TTL:** 1800 seconds (30 minutes)

### 3.2. Product Cache Key Structure

**Key Pattern:** `product:{product_id}`

**Example:** `product:prod_12345`

**Value (JSON String):**
```json
{
  "product_id": "string",
  "product_name": "string",
  "product_description": "string",
  "original_price": "number",
  "discount_price": "number",
  "currency": "VND|USD",
  "images": ["string"],
  "shop_id": "string",
  "shop_name": "string",
  "shop_url": "string",
  "category1": "string",
  "category2": "string",
  "category3": "string",
  "status": "available|out_of_stock",
  "count": "number",
  "rating": "number",
  "review_count": "number",
  "updated_at": "string (ISO 8601)"
}
```

**TTL:** 3600 seconds (1 hour)

### 3.3. User Context Key Structure

**Key Pattern:** `user:{user_id}:context`

**Example:** `user:user_123:context`

**Value (JSON String):**
```json
{
  "user_id": "string",
  "total_sessions": "number",
  "total_messages": "number",
  "favorite_categories": ["string"],
  "favorite_brands": ["string"],
  "average_price_range": {
    "min": "number",
    "max": "number"
  },
  "purchase_history_summary": {
    "total_orders": "number",
    "total_spent": "number",
    "last_purchase_date": "string (ISO 8601)"
  },
  "preferences": {
    "notification_enabled": "boolean",
    "language": "vi|en",
    "currency": "VND|USD"
  },
  "last_updated": "string (ISO 8601)"
}
```

**TTL:** 86400 seconds (24 hours)

### 3.4. Redis Operations

**GET Session:**
```bash
# Command
GET session:550e8400-e29b-41d4-a716-446655440000

# Response (JSON string)
"{\"user_id\":\"user_123\",\"messages\":[...],\"context\":{...}}"
```

**SET Session:**
```bash
# Command
SETEX session:550e8400-e29b-41d4-a716-446655440000 1800 "{\"user_id\":\"user_123\",...}"

# Response
OK
```

**Extend TTL:**
```bash
# Command
EXPIRE session:550e8400-e29b-41d4-a716-446655440000 1800

# Response
(integer) 1
```

---

## 4. CHAT API SERVICE ↔ KAFKA

### 4.1. Topic: `chat-requests` (Producer: Chat API, Consumer: AI Service)

**Message Key:** `session_id` (for partitioning)

**Message Value:**
```json
{
  "message_id": "string (UUID v4)",           // Unique message ID
  "session_id": "string (UUID v4)",           // Session ID
  "user_id": "string",                        // User ID
  "message": "string",                        // User message
  "message_type": "text|voice|image",
  "timestamp": "string (ISO 8601)",           // Message timestamp
  "context": {                                // User context from Redis
    "product_preferences": ["string"],
    "brands": ["string"],
    "price_range": {
      "min": "number",
      "max": "number",
      "currency": "string"
    },
    "last_search": "string",
    "conversation_topics": ["string"]
  },
  "chat_history": [                           // Last 10 messages for context
    {
      "role": "user|assistant",
      "content": "string",
      "timestamp": "string (ISO 8601)"
    }
  ],
  "metadata": {
    "request_id": "string (UUID)",
    "gateway_timestamp": "string (ISO 8601)",
    "client_ip": "string",
    "platform": "string",
    "retry_count": "number"                   // For retry logic
  }
}
```

**Kafka Headers:**
```json
{
  "message-id": "string (UUID v4)",
  "session-id": "string (UUID v4)",
  "user-id": "string",
  "timestamp": "string (ISO 8601)",
  "content-type": "application/json",
  "producer": "chat-api-service",
  "version": "1.0.0"
}
```

### 4.2. Topic: `chat-responses` (Producer: AI Service, Consumer: Chat API)

**Message Key:** `session_id` (for partitioning)

**Message Value:**
```json
{
  "message_id": "string (UUID v4)",           // Original message ID
  "session_id": "string (UUID v4)",
  "user_id": "string",
  "response": "string",                       // AI generated response
  "response_type": "text|product_recommendation|order_confirmation|error",
  "timestamp": "string (ISO 8601)",
  "products": [                               // Product recommendations
    {
      "product_id": "string",
      "product_name": "string",
      "product_url": "string",
      "original_price": "number",
      "discount_price": "number",
      "currency": "string",
      "images": ["string"],
      "shop": {
        "shop_id": "string",
        "shop_name": "string",
        "shop_url": "string"
      },
      "category1": "string",
      "category2": "string",
      "status": "string",
      "count": "number",
      "rating": "number",
      "review_count": "number",
      "relevance_score": "number"             // 0-1, how relevant to query
    }
  ],
  "intent": "string",                         // Detected intent
  "entities": {                               // Extracted entities
    "product_names": ["string"],
    "brands": ["string"],
    "categories": ["string"],
    "price_mentions": [
      {
        "min": "number",
        "max": "number",
        "currency": "string"
      }
    ],
    "quantities": ["number"]
  },
  "confidence": "number",                     // 0-1, confidence score
  "suggestions": ["string"],                  // Follow-up suggestions
  "quick_actions": [                          // Quick action buttons
    {
      "label": "string",
      "action": "string",
      "payload": {}
    }
  ],
  "metadata": {
    "processing_time_ms": "number",           // AI processing time
    "model_used": "string",                   // e.g., "gpt-4"
    "tokens_used": "number",                  // API tokens consumed
    "database_queries": "number",             // Number of DB queries
    "vector_search_results": "number"         // Vector DB results count
  }
}
```

**Kafka Headers:**
```json
{
  "message-id": "string (UUID v4)",
  "session-id": "string (UUID v4)",
  "correlation-id": "string",                 // Original message ID
  "timestamp": "string (ISO 8601)",
  "content-type": "application/json",
  "producer": "ai-service",
  "version": "1.0.0"
}
```

### 4.3. Topic: `user-events` (Producer: Multiple, Consumer: Analytics Service)

**Message Key:** `user_id`

**Message Value:**
```json
{
  "event_id": "string (UUID v4)",
  "event_type": "message_sent|message_received|product_viewed|product_clicked|add_to_cart|purchase|session_start|session_end",
  "user_id": "string",
  "session_id": "string (UUID v4)",
  "timestamp": "string (ISO 8601)",
  "properties": {                             // Event-specific properties
    "product_id": "string",                   // For product events
    "category": "string",
    "price": "number",
    "message_length": "number",               // For message events
    "response_time_ms": "number"
  },
  "metadata": {
    "platform": "string",
    "device_type": "string",
    "location": "string",
    "referrer": "string"
  }
}
```

---

## 5. AI SERVICE ↔ DATABASES

### 5.1. PostgreSQL Queries

#### Query Products by Filters

**SQL:**
```sql
SELECT 
    p.product_id,
    p.product_name,
    p.product_description,
    p.images,
    p.original_price,
    p.discount_price,
    p.count,
    p.category1,
    p.category2,
    p.category3,
    p.status,
    s.shop_id,
    s.shop_name,
    s.shop_url,
    s.shop_description,
    s.phone_number,
    s.address
FROM products p
JOIN shops s ON p.shop_id = s.shop_id
WHERE 
    p.product_name ILIKE $1                -- Search term
    AND p.discount_price BETWEEN $2 AND $3 -- Price range
    AND p.category1 = ANY($4)              -- Categories
    AND p.status = 'available'
    AND p.count > 0
ORDER BY 
    p.discount_price ASC,
    p.rating DESC
LIMIT $5 OFFSET $6;
```

**Parameters:**
```json
{
  "search_term": "%iPhone 15%",
  "min_price": 0,
  "max_price": 30000000,
  "categories": ["Điện thoại", "Smartphone"],
  "limit": 10,
  "offset": 0
}
```

**Response:**
```json
[
  {
    "product_id": "prod_001",
    "product_name": "iPhone 15 Pro Max 256GB",
    "product_description": "...",
    "images": ["img1.jpg", "img2.jpg"],
    "original_price": 32000000,
    "discount_price": 29500000,
    "count": 50,
    "category1": "Điện thoại",
    "category2": "iPhone",
    "category3": "Apple",
    "status": "available",
    "shop_id": "shop_001",
    "shop_name": "TechZone Vietnam",
    "shop_url": "https://shop.example.com/techzone",
    "shop_description": "...",
    "phone_number": "0901234567",
    "address": "123 Nguyen Trai, Hanoi"
  }
]
```

#### Create Order

**SQL:**
```sql
INSERT INTO orders (
    order_id,
    product_id,
    product_name,
    count,
    original_price,
    discount_price,
    price_summary,
    shop,
    shop_id,
    product_url,
    date_time,
    status_payment,
    user_name,
    user_id,
    user_phone_number,
    user_addr
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
)
RETURNING order_id;
```

**Parameters:**
```json
{
  "order_id": "order_550e8400",
  "product_id": "prod_001",
  "product_name": "iPhone 15 Pro Max 256GB",
  "count": 1,
  "original_price": 32000000,
  "discount_price": 29500000,
  "price_summary": 29500000,
  "shop": "TechZone Vietnam",
  "shop_id": "shop_001",
  "product_url": "https://shop.example.com/product/001",
  "date_time": "2025-10-28T10:30:00Z",
  "status_payment": "pending",
  "user_name": "Nguyen Van A",
  "user_id": "user_123",
  "user_phone_number": "0901234567",
  "user_addr": "456 Le Loi, Hanoi"
}
```

#### Get Shop Info

**SQL:**
```sql
SELECT 
    shop_id,
    shop_name,
    shop_description,
    shop_url,
    phone_number,
    address
FROM shops
WHERE shop_id = $1;
```

**Parameters:**
```json
{
  "shop_id": "shop_001"
}
```

**Response:**
```json
{
  "shop_id": "shop_001",
  "shop_name": "TechZone Vietnam",
  "shop_description": "Cửa hàng công nghệ uy tín",
  "shop_url": "https://shop.example.com/techzone",
  "phone_number": "0901234567",
  "address": "123 Nguyen Trai, Hanoi"
}
```

### 5.2. MongoDB Operations

#### Save Conversation Log

**Collection:** `conversations`

**Document:**
```json
{
  "_id": "ObjectId",
  "session_id": "string (UUID v4)",
  "user_id": "string",
  "message_id": "string (UUID v4)",
  "timestamp": "ISODate",
  "user_message": "string",
  "ai_response": "string",
  "products_recommended": [
    {
      "product_id": "string",
      "product_name": "string",
      "price": "number",
      "clicked": "boolean"                    // Did user click?
    }
  ],
  "intent": "string",
  "entities": {},
  "confidence": "number",
  "processing_time_ms": "number",
  "metadata": {
    "platform": "string",
    "device_type": "string",
    "location": "string"
  },
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Index:**
```javascript
// MongoDB Indexes
db.conversations.createIndex({ "session_id": 1 });
db.conversations.createIndex({ "user_id": 1, "timestamp": -1 });
db.conversations.createIndex({ "created_at": 1 }, { expireAfterSeconds: 7776000 }); // 90 days
```

#### Save User Interaction

**Collection:** `user_interactions`

**Document:**
```json
{
  "_id": "ObjectId",
  "event_id": "string (UUID v4)",
  "event_type": "product_viewed|product_clicked|add_to_cart|purchase|search",
  "user_id": "string",
  "session_id": "string (UUID v4)",
  "timestamp": "ISODate",
  "product_id": "string",                     // Optional
  "category": "string",                       // Optional
  "search_query": "string",                   // For search events
  "dwell_time_seconds": "number",             // Time spent
  "metadata": {
    "referrer": "string",
    "utm_source": "string",
    "utm_medium": "string",
    "utm_campaign": "string"
  },
  "created_at": "ISODate"
}
```

### 5.3. Pinecone Vector Database

#### Query Vectors (Semantic Search)

**API Endpoint:** `POST /query`

**Request:**
```json
{
  "vector": [0.123, -0.456, 0.789, ...],      // 3072 dimensions (text-embedding-3-large)
  "top_k": 10,                                // Number of results
  "include_metadata": true,                   // Include product metadata
  "filter": {                                 // Optional metadata filters
    "category": { "$eq": "Điện thoại" },
    "price": { "$lte": 30000000 },
    "status": { "$eq": "available" }
  },
  "namespace": "products"                     // Optional namespace
}
```

**Response:**
```json
{
  "matches": [
    {
      "id": "prod_001",                       // Product ID
      "score": 0.95,                          // Similarity score (0-1)
      "values": [],                           // Vector values (optional)
      "metadata": {                           // Product metadata
        "product_name": "iPhone 15 Pro Max",
        "category": "Điện thoại",
        "price": 29500000,
        "shop_id": "shop_001",
        "description": "...",
        "status": "available"
      }
    },
    {
      "id": "prod_002",
      "score": 0.89,
      "metadata": { /* ... */ }
    }
  ],
  "namespace": "products"
}
```

#### Upsert Vectors (Add/Update Products)

**API Endpoint:** `POST /vectors/upsert`

**Request:**
```json
{
  "vectors": [
    {
      "id": "prod_001",
      "values": [0.123, -0.456, 0.789, ...],  // 3072 dimensions
      "metadata": {
        "product_name": "iPhone 15 Pro Max",
        "product_description": "...",
        "category": "Điện thoại",
        "price": 29500000,
        "shop_id": "shop_001",
        "status": "available",
        "updated_at": "2025-10-28T10:00:00Z"
      }
    }
  ],
  "namespace": "products"
}
```

**Response:**
```json
{
  "upserted_count": 1
}
```

---

## 6. DATA MODELS SUMMARY

### 6.1. PostgreSQL Schema

```sql
-- Products Table
CREATE TABLE products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    product_description TEXT,
    images TEXT[],                            -- Array of image URLs
    original_price NUMERIC(15, 2),
    discount_price NUMERIC(15, 2),
    count INTEGER DEFAULT 0,
    category1 VARCHAR(100),
    category2 VARCHAR(100),
    category3 VARCHAR(100),
    status VARCHAR(20) DEFAULT 'available',
    shop_id VARCHAR(50) REFERENCES shops(shop_id),
    product_url TEXT,
    rating NUMERIC(3, 2) DEFAULT 0.0,
    review_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_product_name ON products USING gin(to_tsvector('english', product_name));
CREATE INDEX idx_category ON products(category1, category2);
CREATE INDEX idx_price ON products(discount_price);
CREATE INDEX idx_status ON products(status);

-- Shops Table
CREATE TABLE shops (
    shop_id VARCHAR(50) PRIMARY KEY,
    shop_name VARCHAR(255) NOT NULL,
    shop_description TEXT,
    shop_url TEXT,
    phone_number VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Orders Table
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES products(product_id),
    product_name VARCHAR(255),
    count INTEGER,
    original_price NUMERIC(15, 2),
    discount_price NUMERIC(15, 2),
    price_summary NUMERIC(15, 2),
    shop VARCHAR(255),
    shop_id VARCHAR(50) REFERENCES shops(shop_id),
    product_url TEXT,
    date_time TIMESTAMP DEFAULT NOW(),
    status_payment VARCHAR(50),
    user_name VARCHAR(255),
    user_id VARCHAR(50),
    user_phone_number VARCHAR(20),
    user_addr TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_order_user ON orders(user_id, date_time DESC);
CREATE INDEX idx_order_status ON orders(status_payment);
```

### 6.2. MongoDB Schema

```javascript
// conversations collection
{
  _id: ObjectId,
  session_id: String,
  user_id: String,
  message_id: String,
  timestamp: Date,
  user_message: String,
  ai_response: String,
  products_recommended: [
    {
      product_id: String,
      product_name: String,
      price: Number,
      clicked: Boolean
    }
  ],
  intent: String,
  entities: Object,
  confidence: Number,
  processing_time_ms: Number,
  metadata: Object,
  created_at: Date,
  updated_at: Date
}

// user_interactions collection
{
  _id: ObjectId,
  event_id: String,
  event_type: String,
  user_id: String,
  session_id: String,
  timestamp: Date,
  product_id: String,
  category: String,
  search_query: String,
  dwell_time_seconds: Number,
  metadata: Object,
  created_at: Date
}
```

### 6.3. Redis Key Patterns

```
# Session keys
session:{session_id}                          → JSON (Session data)
TTL: 1800 seconds

# Product cache
product:{product_id}                          → JSON (Product data)
TTL: 3600 seconds

# User context
user:{user_id}:context                        → JSON (User preferences)
TTL: 86400 seconds

# Shop cache
shop:{shop_id}                                → JSON (Shop data)
TTL: 3600 seconds

# Rate limiting
ratelimit:{user_id}:{window}                  → Number (Request count)
TTL: 60 seconds

# Active sessions list
active_sessions                               → Set (Session IDs)
TTL: None (updated manually)
```

---

## 7. AUTHENTICATION & AUTHORIZATION

### 7.1. JWT Token Structure

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_123",                        // User ID
    "email": "user@example.com",
    "name": "Nguyen Van A",
    "role": "user|admin|premium",
    "iat": 1698483600,                        // Issued at
    "exp": 1698570000,                        // Expires at
    "permissions": [
      "chat:send",
      "chat:receive",
      "product:view",
      "order:create"
    ]
  },
  "signature": "..."
}
```

### 7.2. API Key for Service-to-Service

**Header:**
```
X-API-Key: service_key_abc123xyz
X-Service-Name: ai-service
```

---

## 8. ERROR CODES & HTTP STATUS

### 8.1. HTTP Status Codes

| Code | Status | Usage |
|------|--------|-------|
| 200 | OK | Successful GET request |
| 201 | Created | Successful POST creating resource |
| 202 | Accepted | Request accepted for async processing |
| 400 | Bad Request | Invalid request format |
| 401 | Unauthorized | Authentication failed |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service down |

### 8.2. Application Error Codes

| Code | Message | Description |
|------|---------|-------------|
| `SESSION_NOT_FOUND` | Session not found | Invalid session_id |
| `SESSION_EXPIRED` | Session expired | Session TTL expired |
| `INVALID_MESSAGE` | Invalid message format | Message validation failed |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded | Too many requests |
| `AI_SERVICE_ERROR` | AI service error | AI processing failed |
| `DATABASE_ERROR` | Database error | Database query failed |
| `PRODUCT_NOT_FOUND` | Product not found | Product ID doesn't exist |
| `ORDER_CREATE_FAILED` | Order creation failed | Failed to create order |
| `PAYMENT_FAILED` | Payment failed | Payment processing error |

---

## 9. VERSIONING & BACKWARD COMPATIBILITY

### 9.1. API Versioning

**URL-based versioning:**
```
/api/v1/chat/message
/api/v2/chat/message
```

**Header-based versioning:**
```
Accept: application/vnd.api+json; version=1.0
```

### 9.2. Message Format Versioning

**Kafka message headers:**
```json
{
  "schema-version": "1.0.0",
  "message-format": "json"
}
```

**Backward compatibility rules:**
- Never remove fields, only add new ones
- Use optional fields for new features
- Maintain old field names, add new ones
- Document breaking changes clearly

---

## 10. PERFORMANCE CONSIDERATIONS

### 10.1. Message Size Limits

| Component | Max Size | Recommendation |
|-----------|----------|----------------|
| User message | 1000 chars | Keep under 500 |
| AI response | 5000 chars | Keep under 2000 |
| Kafka message | 1 MB | Keep under 100 KB |
| Redis value | 512 MB | Keep under 1 MB |
| HTTP body | 10 MB | Keep under 1 MB |

### 10.2. Timeout Configuration

| Operation | Timeout | Retry |
|-----------|---------|-------|
| Gateway → Chat API | 30s | No |
| Chat API → Redis | 1s | 3x |
| Chat API → Kafka | 5s | 3x |
| AI Service → LLM | 30s | 1x |
| AI Service → PostgreSQL | 10s | 2x |
| AI Service → Pinecone | 5s | 2x |

---

## 11. MONITORING METRICS

### 11.1. Key Metrics to Track

**Application Metrics:**
```json
{
  "total_messages_sent": "counter",
  "total_messages_received": "counter",
  "active_sessions": "gauge",
  "average_response_time_ms": "histogram",
  "error_rate": "gauge",
  "kafka_lag": "gauge",
  "redis_hit_rate": "gauge",
  "ai_token_usage": "counter"
}
```

**Business Metrics:**
```json
{
  "daily_active_users": "gauge",
  "messages_per_session": "histogram",
  "product_click_through_rate": "gauge",
  "order_conversion_rate": "gauge",
  "revenue_per_session": "histogram"
}
```

---

## CHECKLIST FOR IMPLEMENTATION

- [ ] Define all API contracts in OpenAPI/Swagger format
- [ ] Create JSON schemas for all message formats
- [ ] Set up request/response validation middleware
- [ ] Implement proper error handling with error codes
- [ ] Add request tracing with correlation IDs
- [ ] Set up monitoring for all key metrics
- [ ] Implement rate limiting at Gateway level
- [ ] Add circuit breakers for external services
- [ ] Set up alerting for error rates and latency
- [ ] Document all data structures in team wiki
- [ ] Create Postman/Insomnia collections for testing
- [ ] Write integration tests for all APIs
- [ ] Set up staging environment with sample data
- [ ] Perform load testing with realistic traffic

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-10-28  
**Maintained by:** AI VNPOST