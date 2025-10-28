CREATE TABLE orders (
    order_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),  -- NULL for guest orders
    device_id VARCHAR(255),  -- For guest orders
    session_id UUID,
    
    -- Customer info
    customer_name VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    customer_email VARCHAR(255),
    
    -- Delivery
    delivery_address TEXT NOT NULL,
    delivery_city VARCHAR(100),
    delivery_district VARCHAR(100),
    delivery_notes TEXT,
    
    -- Order details
    products JSONB NOT NULL,
    total_amount DECIMAL(12, 2),
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    payment_status VARCHAR(50) DEFAULT 'pending',
    
    -- Tracking
    is_guest BOOLEAN DEFAULT FALSE,
    claimed_at TIMESTAMP,  -- When guest order was claimed by user
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Index for guest orders
    INDEX idx_device_id (device_id),
    INDEX idx_user_device (user_id, device_id)
);