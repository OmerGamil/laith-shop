from django.shortcuts import render

def home(request):
    products = []
    for i in range(1, 9):
        products.append({
            'title': f'Product {i}',
            'image_url': 'static/shop/assets/product.jpeg',
            'show_sale': i % 2 == 0,
            'price_html': "$25.00" if i % 3 == 0 else "$40.00 - $80.00"
        })
    return render(request, 'shop/index.html', {'products': products})
