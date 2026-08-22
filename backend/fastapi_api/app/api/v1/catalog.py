from django.db.models import Q
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.products.models import Category, Product
from core.domain.auth import AuthenticatedUser
from fastapi_api.app.dependencies.auth import get_current_user
from fastapi_api.app.schemas.catalog import CategoryResponse, ProductResponse

router = APIRouter()


def _product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        branch_id=product.branch_id,
        category_id=product.category_id,
        category_name=product.category.name,
        sku=product.sku,
        barcode=product.barcode,
        name=product.name,
        description=product.description,
        selling_price=product.selling_price,
        cost_price=product.cost_price,
        unit=product.unit,
        tax_status=product.tax_status,
        track_inventory=product.track_inventory,
        reorder_level=product.reorder_level,
        image_url=product.image.url if product.image else None,
        is_active=product.is_active,
    )


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(
    branch_id: int | None = None,
    include_inactive: bool = False,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    queryset = Category.objects.all().order_by("sort_order", "name")
    resolved_branch = branch_id or current_user.branch_id
    if resolved_branch:
        queryset = queryset.filter(branch_id=resolved_branch)
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return [
        CategoryResponse(
            id=category.id,
            branch_id=category.branch_id,
            name=category.name,
            sort_order=category.sort_order,
            is_active=category.is_active,
        )
        for category in queryset
    ]


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    branch_id: int | None = None,
    category_id: int | None = None,
    q: str | None = Query(default=None, min_length=1),
    include_inactive: bool = False,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    queryset = Product.objects.select_related("category").order_by("name")
    resolved_branch = branch_id or current_user.branch_id
    if resolved_branch:
        queryset = queryset.filter(branch_id=resolved_branch)
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q)
        )
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return [_product_response(product) for product in queryset]


@router.get("/products/lookup", response_model=ProductResponse)
def lookup_product(
    code: str = Query(..., min_length=1, max_length=80),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    needle = code.strip()
    queryset = Product.objects.select_related("category").filter(is_active=True)
    if current_user.branch_id:
        queryset = queryset.filter(branch_id=current_user.branch_id)
    product = queryset.filter(barcode__iexact=needle).exclude(barcode="").first()
    if product is None:
        product = queryset.filter(sku__iexact=needle).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _product_response(product)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    product = Product.objects.select_related("category").filter(pk=product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _product_response(product)
