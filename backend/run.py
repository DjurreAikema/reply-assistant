from app import create_app

app = create_app()

if __name__ == "__main__":
    # Port 5000 is what the Angular dev proxy points at. Change both
    # together or the frontend silently gets connection errors.
    app.run(port=5000, debug=True)
