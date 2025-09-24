from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Float, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, nullable=False, unique=True)
    is_admin = Column(Boolean, default=False)

    cart_items = relationship("CartItem", back_populates="user")


class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    products = relationship('Product', back_populates='category')


class Product(Base):
    __tablename__ = 'product'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    photo_url = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'))

    category = relationship('Category', back_populates='products')
    sizes = relationship('Size', back_populates='product')
    cart_items = relationship('CartItem', back_populates='product')


class Size(Base):
    __tablename__ = 'size'
    id = Column(Integer, primary_key=True)
    size = Column(Float, nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'))

    product = relationship('Product', back_populates='sizes')
    cart_items = relationship('CartItem', back_populates='size')


class CartItem(Base):
    __tablename__ = 'cart_item'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    product_id = Column(Integer, ForeignKey('product.id'))
    size_id = Column(Integer, ForeignKey('size.id'))
    quantity = Column(Integer, nullable=False)

    user = relationship("User", back_populates="cart_items")
    product = relationship('Product', back_populates='cart_items')
    size = relationship('Size', back_populates='cart_items')


def create_tables(engine):
    Base.metadata.create_all(engine)