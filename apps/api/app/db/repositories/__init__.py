from app.db.repositories.cart import CartItemRepository, CartRepository
from app.db.repositories.carts import (
    CartRepositoryProtocol,
    InMemoryCartRepository,
    SupabaseCartRepository,
)
from app.db.repositories.catalog import CatalogRepository
from app.db.repositories.checkouts import (
    CheckoutRepositoryProtocol,
    InMemoryCheckoutRepository,
    SupabaseCheckoutRepository,
)
from app.db.repositories.conversations import (
    ConversationRepository,
    InMemoryConversationRepository,
    SupabaseConversationRepository,
)
from app.db.repositories.customers import (
    CustomerRepository,
    InMemoryCustomerRepository,
    SupabaseCustomerRepository,
)
from app.db.repositories.inventory import InventoryRepository
from app.db.repositories.marketing import (
    InMemoryMarketingRepository,
    MarketingRepositoryProtocol,
    SupabaseMarketingRepository,
)
from app.db.repositories.messages import (
    InMemoryMessageRepository,
    MessageRepository,
    SupabaseMessageRepository,
)
from app.db.repositories.order import OrderItemRepository, OrderRepository
from app.db.repositories.orders import (
    InMemoryOrderRepository,
    OrderRepositoryProtocol,
    SupabaseOrderRepository,
)
from app.db.repositories.payments import (
    InMemoryPaymentRepository,
    PaymentRepositoryProtocol,
    SupabasePaymentRepository,
)
from app.db.repositories.product import ProductRepository, ProductVariantRepository
from app.db.repositories.store import DomainRepository, StoreRepository

__all__ = [
    "StoreRepository",
    "DomainRepository",
    "CatalogRepository",
    "ProductRepository",
    "ProductVariantRepository",
    "InventoryRepository",
    "CartRepository",
    "CartItemRepository",
    "CartRepositoryProtocol",
    "SupabaseCartRepository",
    "InMemoryCartRepository",
    "OrderRepository",
    "OrderItemRepository",
    "OrderRepositoryProtocol",
    "SupabaseOrderRepository",
    "InMemoryOrderRepository",
    "ConversationRepository",
    "SupabaseConversationRepository",
    "InMemoryConversationRepository",
    "MessageRepository",
    "SupabaseMessageRepository",
    "InMemoryMessageRepository",
    "CustomerRepository",
    "SupabaseCustomerRepository",
    "InMemoryCustomerRepository",
    "CheckoutRepositoryProtocol",
    "SupabaseCheckoutRepository",
    "InMemoryCheckoutRepository",
    "PaymentRepositoryProtocol",
    "SupabasePaymentRepository",
    "InMemoryPaymentRepository",
    "MarketingRepositoryProtocol",
    "SupabaseMarketingRepository",
    "InMemoryMarketingRepository",
]
