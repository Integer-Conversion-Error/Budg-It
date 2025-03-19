# Budg-It

## Overview
Budg-It is an independent, AI-powered budgeting tool designed to help users efficiently manage their finances. By leveraging intelligent automation, Budg-It simplifies the process of tracking expenses, categorizing transactions, and optimizing personal or business budgets.

This project is **not affiliated** with any organization and is developed as an independent initiative to provide accessible financial management tools to the community.

## Features
- **AI Integration**: Uses automation to provide smart budgeting recommendations.
- **Receipt Scanning**: Extracts and categorizes expenses from scanned receipts.
- **Web Interface**: User-friendly web interface for easy budget management.
- **Data Security**: All financial data is processed locally, ensuring user privacy.

## Installation
### 1. Clone the Repository
```bash
git clone https://github.com/Integer-Conversion-Error/Budg-It.git
```

### 2. Navigate to the Project Directory
```bash
cd Budg-It
```

### 3. Create a Virtual Environment (Recommended)
Setting up a virtual environment ensures dependencies are managed efficiently.

- On Windows:
  ```bash
  python -m venv env
  env\Scripts\activate
  ```
- On macOS/Linux:
  ```bash
  python3 -m venv env
  source env/bin/activate
  ```

### 4. Install Dependencies
Once the virtual environment is activated, install all necessary libraries from `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Usage
### Running the Console Application
```bash
python consolemain.py
```
This starts the interactive console tool for managing budgets.

### Running the Web Application
To launch the web-based budgeting tool:
```bash
python host_page.py
```
Once running, open a web browser and visit:
```
http://127.0.0.1:5000
```

## Receipt Scanning Feature
Budg-It includes a feature that allows users to scan receipts for automatic expense logging.

1. Ensure the receipt image is clear and stored in the `static` directory.
2. Run the receipt scanner module:
   ```bash
   python receipt_reader.py
   ```
3. The tool will extract transaction details and categorize expenses automatically.

## Dependencies
Budg-It relies on several Python libraries, all of which are listed in `requirements.txt`. Some key dependencies include:
- `Flask` (for web application hosting)
- `OpenAI` (for AI-driven features, if applicable)
- `Pillow` and `pytesseract` (for receipt scanning and image processing)

To install them, ensure you run:
```bash
pip install -r requirements.txt
```
inside your virtual environment.

## Contributing
Budg-It is an independent project, and contributions are welcome. To contribute:
1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Description of feature"
   ```
4. Push the branch:
   ```bash
   git push origin feature-name
   ```
5. Open a pull request with details of the proposed changes.

## License
Budg-It is released under the [MIT License](LICENSE). Feel free to use, modify, and distribute it as needed.

## Acknowledgements
This project is independently developed and maintained. Contributions and feedback from the community are always appreciated!

