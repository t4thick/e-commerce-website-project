# Crispy Clucker's Food Truck

A professional e-commerce platform for a fried chicken food truck, built with Flask.

## Features

- **Customer Portal**: Browse menu, add to cart, checkout
- **Staff System**: Role-based access with unique registration codes
- **Manager Dashboard**: View orders, update status, track revenue
- **OTP Authentication**: Secure login with one-time passwords

## Tech Stack

- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Payments**: Stripe
- **Frontend**: Jinja2 templates, vanilla CSS

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/t4thick/e-commerce-website-project.git
cd e-commerce-website-project
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment:
```bash
cp .env.example .env
# Edit .env with your values
```

5. Run the app:
```bash
python run.py
```

6. Open http://127.0.0.1:5000

## Project Structure

```
crispy-cluckers-flask/
├── app/
│   ├── __init__.py       # App factory
│   ├── models.py         # Database models
│   ├── routes/
│   │   ├── main.py       # Homepage, menu
│   │   ├── auth.py       # Login, signup, OTP
│   │   ├── cart.py       # Cart, checkout
│   │   └── manager.py    # Staff dashboard
│   ├── static/
│   │   └── css/
│   │       └── style.css
│   └── templates/
│       ├── base.html
│       ├── home.html
│       └── ...
├── config.py
├── run.py
├── requirements.txt
└── README.md
```

## Staff Codes

Default codes for testing:
- `ADMIN2024` - Admin access
- `MANAGER2024` - Manager access
- `STAFF2024` - Staff access

## License

MIT

