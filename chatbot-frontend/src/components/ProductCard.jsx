// src/components/ProductCard.jsx
import './ProductCard.css';

const ProductCard = ({ product }) => {
  const formatPrice = (price) => {
    return new Intl.NumberFormat('vi-VN').format(price);
  };
  
  const handleViewShop = () => {
    if (product.shop_url) {
      window.open(product.shop_url, '_blank');
    }
  };
  
  return (
    <div className="product-card">
      <div className="product-image">
        <img 
          src={product.images?.[0] || 'https://via.placeholder.com/200'} 
          alt={product.product_name}
          onError={(e) => {
            e.target.src = 'https://via.placeholder.com/200?text=No+Image';
          }}
        />
        {product.status === 'out_of_stock' && (
          <div className="out-of-stock-badge">Hết hàng</div>
        )}
      </div>
      
      <div className="product-info">
        <h4 className="product-name" title={product.product_name}>
          {product.product_name}
        </h4>
        
        <div className="product-price">
          {product.original_price !== product.discount_price && (
            <span className="price-original">
              {formatPrice(product.original_price)} đ
            </span>
          )}
          <span className="price-discount">
            {formatPrice(product.discount_price)} đ
          </span>
        </div>
        
        {product.original_price !== product.discount_price && (
          <div className="discount-badge">
            -{Math.round((1 - product.discount_price / product.original_price) * 100)}%
          </div>
        )}
        
        <div className="product-shop">
          <span className="shop-icon">🏪</span>
          <span className="shop-name">{product.shop_name}</span>
        </div>
        
        {product.rating && (
          <div className="product-rating">
            <span className="rating-stars">⭐ {product.rating.toFixed(1)}</span>
            {product.review_count && (
              <span className="review-count">({product.review_count})</span>
            )}
          </div>
        )}
      </div>
      
      <div className="product-actions">
        <button 
          className="btn-view-shop" 
          onClick={handleViewShop}
          disabled={!product.shop_url}
        >
          Xem shop
        </button>
        <button 
          className="btn-add-cart"
          disabled={product.status === 'out_of_stock'}
        >
          Thêm vào giỏ
        </button>
      </div>
    </div>
  );
};

export default ProductCard;