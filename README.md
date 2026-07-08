# 🚘 Car Deal Analyzer

Car Deal Analyzer is a Python desktop application designed to analyze car listings and evaluate whether a vehicle represents a potentially good deal compared to current market values.

Buying a used car often requires comparing many listings, understanding average market prices, and identifying vehicles that are priced below their expected value. This process can be difficult and time-consuming when done manually.

Car Deal Analyzer solves this problem by collecting vehicle data, analyzing listings against market information, and helping users identify potentially valuable offers more efficiently.

The application provides users with a data-driven approach to evaluating car listings instead of relying only on manual price comparisons.

## Features

- Automated monitoring of car listings
- Market value analysis of vehicles
- Comparison between listing prices and estimated market values
- Detection of potentially undervalued offers
- Telegram notifications for interesting deals
- SQLite database for storing vehicle data
- User-friendly Tkinter desktop interface
- Automated data collection using Playwright

## Technologies Used

- Python
- Playwright
- SQLite
- Tkinter
- Telegram Bot API

## How It Works

1. The application collects vehicle listing data from supported marketplaces.
2. Vehicle information is stored and organized in a local SQLite database.
3. Listings are analyzed and compared with available market data.
4. The application evaluates whether a vehicle price matches or differs from expected market values.
5. When a potentially good deal is identified, a Telegram notification can be sent.

This allows users to make faster and more informed decisions when searching for used vehicles.

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

Install Playwright browser:

```bash
playwright install
```

Run the application:

```bash
python carscope.py
```

## Project Purpose

Car Deal Analyzer was developed to solve a common problem in the used car market: finding fairly priced vehicles among thousands of available listings.

The goal of the project was to create a practical application that uses automation and data analysis to help users evaluate car offers more efficiently.

The project demonstrates practical software development skills through:

- Data collection and processing
- Web scraping and automation
- Market data analysis
- Database integration
- API integration
- Desktop application development
- Real-world problem solving

## Future Improvements

- More advanced price prediction models
- Historical price tracking
- Vehicle reliability scoring
- Additional marketplace support
- Advanced filtering options
- Machine learning based deal recommendations

## Author

Mihajlo Blagojevic
