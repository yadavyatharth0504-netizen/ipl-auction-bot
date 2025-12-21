import os
import json
import logging
import random
import psycopg2
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Flask

# --- CONFIGURATION ---
TOKEN = "8370192102:AAEDaW7LCGRLqHB8PUprLOxUDhYm1eYhKO8" 
DB_URI = os.getenv("DATABASE_URL")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIG CONSTANTS ---
PURSE_LIMIT = 120.0
MAX_SQUAD_SIZE = 15
MAX_FOREIGNERS = 6
MIN_WICKETKEEPERS = 1
MIN_BOWLING_OPTIONS = 6

# --- MASTER PLAYER LIST (ALL 250 PLAYERS) ---
MASTER_PLAYER_LIST = [
    {"id": 1, "name": "KL Rahul", "role": "Wicketkeeper", "nat": "Indian", "base": 2.0},
    {"id": 2, "name": "Ishan Kishan", "role": "Wicketkeeper", "nat": "Indian", "base": 2.0},
    {"id": 3, "name": "Dhruv Jurel", "role": "Wicketkeeper", "nat": "Indian", "base": 2.0},
    {"id": 4, "name": "Jitesh Sharma", "role": "Wicketkeeper", "nat": "Indian", "base": 2.0},
    {"id": 5, "name": "Rishabh Pant", "role": "Wicketkeeper", "nat": "Indian", "base": 2.0},
    {"id": 6, "name": "Sanju Samson", "role": "Wicketkeeper", "nat": "Indian", "base": 2.0},
    {"id": 7, "name": "MS Dhoni", "role": "Wicketkeeper", "nat": "Indian", "base": 2.0},
    {"id": 8, "name": "Shreyas Iyer", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 9, "name": "Suryakumar Yadav", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 10, "name": "Yashasvi Jaiswal", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 11, "name": "Sai Sudharsan", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 12, "name": "Ruturaj Gaikwad", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 13, "name": "Shubman Gill", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 14, "name": "Prabhsimran Singh", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 15, "name": "Priyansh Arya", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 16, "name": "Ajinkya Rahane", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 17, "name": "Rajat Patidar", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 18, "name": "Virat Kohli", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 19, "name": "Abhishek Sharma", "role": "Allrounder", "nat": "Indian", "base": 2.0},
    {"id": 20, "name": "Hardik Pandya", "role": "Allrounder", "nat": "Indian", "base": 2.0},
    {"id": 21, "name": "Riyan Parag", "role": "Allrounder", "nat": "Indian", "base": 2.0},
    {"id": 22, "name": "Axar Patel", "role": "Allrounder", "nat": "Indian", "base": 2.0},
    {"id": 23, "name": "Ravindra Jadeja", "role": "Allrounder", "nat": "Indian", "base": 2.0},
    {"id": 24, "name": "Krunal Pandya", "role": "Allrounder", "nat": "Indian", "base": 2.0},
    {"id": 25, "name": "Shivam Dube", "role": "Allrounder", "nat": "Indian", "base": 2.0},
    {"id": 26, "name": "Prasidh Krishna", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 27, "name": "Jasprit Bumrah", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 28, "name": "Arshdeep Singh", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 29, "name": "Mohammed Siraj", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 30, "name": "Varun Chakravarthy", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 31, "name": "Kuldeep Yadav", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 32, "name": "Bhuvneshwar Kumar", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 33, "name": "Harshit Rana", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 34, "name": "Nicholas Pooran", "role": "Wicketkeeper", "nat": "Foreign", "base": 2.0},
    {"id": 35, "name": "Jos Buttler", "role": "Wicketkeeper", "nat": "Foreign", "base": 2.0},
    {"id": 36, "name": "Phil Salt", "role": "Wicketkeeper", "nat": "Foreign", "base": 2.0},
    {"id": 37, "name": "Heinrich Klaasen", "role": "Wicketkeeper", "nat": "Foreign", "base": 2.0},
    {"id": 38, "name": "Tristan Stubbs", "role": "Wicketkeeper", "nat": "Foreign", "base": 2.0},
    {"id": 39, "name": "Sunil Narine", "role": "Allrounder", "nat": "Foreign", "base": 2.0},
    {"id": 40, "name": "Aiden Markram", "role": "Allrounder", "nat": "Foreign", "base": 2.0},
    {"id": 41, "name": "Marco Jansen", "role": "Allrounder", "nat": "Foreign", "base": 2.0},
    {"id": 42, "name": "Marcus Stoinis", "role": "Allrounder", "nat": "Foreign", "base": 2.0},
    {"id": 43, "name": "Romario Shepherd", "role": "Allrounder", "nat": "Foreign", "base": 2.0},
    {"id": 44, "name": "Cameron Green", "role": "Allrounder", "nat": "Foreign", "base": 2.0},
    {"id": 45, "name": "Rohit Sharma", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 46, "name": "Mitchell Marsh", "role": "Batter", "nat": "Foreign", "base": 2.0},
    {"id": 47, "name": "Travis Head", "role": "Batter", "nat": "Foreign", "base": 2.0},
    {"id": 48, "name": "Tim David", "role": "Batter", "nat": "Foreign", "base": 2.0},
    {"id": 49, "name": "Dewald Brevis", "role": "Batter", "nat": "Foreign", "base": 2.0},
    {"id": 50, "name": "Pat Cummins", "role": "Bowler", "nat": "Foreign", "base": 2.0},
    {"id": 51, "name": "Trent Boult", "role": "Bowler", "nat": "Foreign", "base": 2.0},
    {"id": 52, "name": "Josh Hazlewood", "role": "Bowler", "nat": "Foreign", "base": 2.0},
    {"id": 53, "name": "Noor Ahmad", "role": "Bowler", "nat": "Foreign", "base": 2.0},
    {"id": 54, "name": "Kagiso Rabada", "role": "Bowler", "nat": "Foreign", "base": 2.0},
    {"id": 55, "name": "Jofra Archer", "role": "Bowler", "nat": "Foreign", "base": 2.0},
    {"id": 56, "name": "Vaibhav Suryavanshi", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 57, "name": "Tilak Varma", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 58, "name": "Devdutt Padikkal", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 59, "name": "Nehal Wadhera", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 60, "name": "Naman Dhir", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 61, "name": "Shashank Singh", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 62, "name": "Angkrish Raghuvanshi", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 63, "name": "Rinku Singh", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 64, "name": "Ashutosh Sharma", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 65, "name": "Ayush Mhatre", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 66, "name": "Ramandeep Singh", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 67, "name": "Aniket Verma", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 68, "name": "Shubham Dube", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 69, "name": "Abishek Porel", "role": "Wicketkeeper", "nat": "Indian", "base": 1.0},
    {"id": 70, "name": "Urvil Patel", "role": "Wicketkeeper", "nat": "Indian", "base": 1.0},
    {"id": 71, "name": "Nitish Kumar Reddy", "role": "Allrounder", "nat": "Indian", "base": 1.0},
    {"id": 72, "name": "Washington Sundar", "role": "Allrounder", "nat": "Indian", "base": 1.0},
    {"id": 73, "name": "Venkatesh Iyer", "role": "Allrounder", "nat": "Indian", "base": 1.0},
    {"id": 74, "name": "Rahul Tewatia", "role": "Allrounder", "nat": "Indian", "base": 1.0},
    {"id": 75, "name": "Ayush Badoni", "role": "Allrounder", "nat": "Indian", "base": 1.0},
    {"id": 76, "name": "Vipraj Nigam", "role": "Allrounder", "nat": "Indian", "base": 1.0},
    {"id": 77, "name": "Harsh Dubey", "role": "Allrounder", "nat": "Indian", "base": 1.0},
    {"id": 78, "name": "Khaleel Ahmed", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 79, "name": "Yash Dayal", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 80, "name": "Deepak Chahar", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 81, "name": "Vaibhav Arora", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 82, "name": "Sai Kishore", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 83, "name": "Digvesh Singh Rathi", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 84, "name": "Harshal Patel", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 85, "name": "Avesh Khan", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 86, "name": "Yuzvendra Chahal", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 87, "name": "Suyash Sharma", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 88, "name": "Mukesh Kumar", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 89, "name": "Shardul Thakur", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 90, "name": "Tushar Deshpande", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 91, "name": "Sandeep Sharma", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 92, "name": "Mohammad Shami", "role": "Bowler", "nat": "Indian", "base": 1.0},
    {"id": 93, "name": "Sherfane Rutherford", "role": "Batter", "nat": "Foreign", "base": 1.0},
    {"id": 94, "name": "Shimron Hetmyer", "role": "Batter", "nat": "Foreign", "base": 1.0},
    {"id": 95, "name": "Glenn Phillips", "role": "Batter", "nat": "Foreign", "base": 1.0},
    {"id": 96, "name": "David Miller", "role": "Batter", "nat": "Foreign", "base": 1.0},
    {"id": 97, "name": "Pathum Nissanka", "role": "Batter", "nat": "Foreign", "base": 1.0},
    {"id": 98, "name": "Ryan Rickelton", "role": "Wicketkeeper", "nat": "Foreign", "base": 1.0},
    {"id": 99, "name": "Quinton de Kock", "role": "Wicketkeeper", "nat": "Foreign", "base": 1.0},
    {"id": 100, "name": "Tim Seifert", "role": "Wicketkeeper", "nat": "Foreign", "base": 1.0},
    {"id": 101, "name": "Will Jacks", "role": "Allrounder", "nat": "Foreign", "base": 1.0},
    {"id": 102, "name": "Mitchell Santner", "role": "Allrounder", "nat": "Foreign", "base": 1.0},
    {"id": 103, "name": "Akeal Hosein", "role": "Allrounder", "nat": "Foreign", "base": 1.0},
    {"id": 104, "name": "Liam Livingstone", "role": "Allrounder", "nat": "Foreign", "base": 1.0},
    {"id": 105, "name": "Sam Curran", "role": "Allrounder", "nat": "Foreign", "base": 1.0},
    {"id": 106, "name": "Rashid Khan", "role": "Bowler", "nat": "Foreign", "base": 1.0},
    {"id": 107, "name": "Mitchell Starc", "role": "Bowler", "nat": "Foreign", "base": 1.0},
    {"id": 108, "name": "Nathan Ellis", "role": "Bowler", "nat": "Foreign", "base": 1.0},
    {"id": 109, "name": "Matheesha Pathirana", "role": "Bowler", "nat": "Foreign", "base": 1.0},
    {"id": 110, "name": "Abdul Samad", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 111, "name": "Shahrukh Khan", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 112, "name": "Karun Nair", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 113, "name": "Nitish Rana", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 114, "name": "Sameer Rizvi", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 115, "name": "Manish Pandey", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 116, "name": "Himmat Singh", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 117, "name": "S Ravichandran", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 118, "name": "Rahul Tripathi", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 119, "name": "Prithvi Shaw", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 120, "name": "Sahil Parakh", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 121, "name": "Akshat Raghuvanshi", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 122, "name": "Danish Malewar", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 123, "name": "Aman Rao", "role": "Batter", "nat": "Indian", "base": 0.5},
    {"id": 124, "name": "Sarfaraz Khan", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 125, "name": "Kartik Sharma", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 126, "name": "Robin Minz", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 127, "name": "Anuj Rawat", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 128, "name": "Kumar Kushagra", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 129, "name": "Vishnu Vinod", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 130, "name": "Tejasvi Dahiya", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 131, "name": "Aman Khan", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 132, "name": "Mukul Choudhary", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 133, "name": "Ravi Singh", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 134, "name": "Salil Arora", "role": "Wicketkeeper", "nat": "Indian", "base": 0.5},
    {"id": 135, "name": "Shahbaz Ahmed", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 136, "name": "Manav Suthar", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 137, "name": "Arjun Tendulkar", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 138, "name": "Prashant Veer", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 139, "name": "Auqib Dar", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 140, "name": "Mangesh Yadav", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 141, "name": "Ramakrishna Ghosh", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 142, "name": "Ajay Mandal", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 143, "name": "Madhav Tiwari", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 144, "name": "Tripurana Vijay", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 145, "name": "Gurnoor Singh Brar", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 146, "name": "Nishant Sindhu", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 147, "name": "Arshin Kulkarni", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 148, "name": "Raj Angad Bawa", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 149, "name": "Harnoor Pannu", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 150, "name": "Musheer Khan", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 151, "name": "Pyla Avinash", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 152, "name": "Suryansh Shedge", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 153, "name": "Abhinandan Singh", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 154, "name": "Swapnil Singh", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 155, "name": "Daksh Kamra", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 156, "name": "Prashant Solanki", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 157, "name": "Sarthak Ranjan", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 158, "name": "Naman Tiwari", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 159, "name": "Atharva Ankolekar", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 160, "name": "Mayank Rawat", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 161, "name": "Satwik Deswal", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 162, "name": "Kanishk Chouhan", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 163, "name": "Vihan Malhotra", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 164, "name": "Vicky Ostwal", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 165, "name": "Shivang Kumar", "role": "Allrounder", "nat": "Indian", "base": 0.5},
    {"id": 166, "name": "T Natarajan", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 167, "name": "Ashwini Kumar", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 168, "name": "Jaydev Unadkat", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 169, "name": "Anshul Kamboj", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 170, "name": "Gurjapneet Singh", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 171, "name": "Arshad Khan", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 172, "name": "Zeeshan Ansari", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 173, "name": "Harpreet Brar", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 174, "name": "Prince Yadav", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 175, "name": "Ishant Sharma", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 176, "name": "Vijaykumar Vyshak", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 177, "name": "Yudhvir Singh", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 178, "name": "Akash Singh", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 179, "name": "Mayank Yadav", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 180, "name": "Umran Malik", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 181, "name": "Mohsin Khan", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 182, "name": "Mayank Markande", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 183, "name": "M Siddharth", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 184, "name": "Rasikh Salam", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 185, "name": "Mukesh Choudhary", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 186, "name": "Yash Thakur", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 187, "name": "Anukul Roy", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 188, "name": "Shreyas Gopal", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 189, "name": "Jayant Yadav", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 190, "name": "Raghu Sharma", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 191, "name": "Akash Deep", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 192, "name": "Kartik Tyagi", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 193, "name": "Rahul Chahar", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 194, "name": "Ravi Bishnoi", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 195, "name": "Ashok Sharma", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 196, "name": "Prithviraj Yarra", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 197, "name": "Mohammad Izhar", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 198, "name": "Vishal Nishad", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 199, "name": "Pravin Dubey", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 200, "name": "Vignesh Puthur", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 201, "name": "Sushant Mishra", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 202, "name": "Yash Raj Punia", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 203, "name": "Brijesh Sharma", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 204, "name": "Kuldeep Sen", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 205, "name": "Krains Fuletra", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 206, "name": "Praful Hinge", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 207, "name": "Amit Kumar", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 208, "name": "Onkar Tarmale", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 209, "name": "Sakib Hussain", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 210, "name": "Shivam Mavi", "role": "Bowler", "nat": "Indian", "base": 0.5},
    {"id": 211, "name": "Tom Banton", "role": "Batter", "nat": "Foreign", "base": 0.5},
    {"id": 212, "name": "Jordan Cox", "role": "Batter", "nat": "Foreign", "base": 0.5},
    {"id": 213, "name": "Jacob Bethell", "role": "Batter", "nat": "Foreign", "base": 0.5},
    {"id": 214, "name": "Matthew Breetzke", "role": "Wicketkeeper", "nat": "Foreign", "base": 0.5},
    {"id": 215, "name": "Donovan Ferreira", "role": "Wicketkeeper", "nat": "Foreign", "base": 0.5},
    {"id": 216, "name": "Finn Allen", "role": "Wicketkeeper", "nat": "Foreign", "base": 0.5},
    {"id": 217, "name": "Josh Inglis", "role": "Wicketkeeper", "nat": "Foreign", "base": 0.5},
    {"id": 218, "name": "Ben Duckett", "role": "Wicketkeeper", "nat": "Foreign", "base": 0.5},
    {"id": 219, "name": "Jamie Overton", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 220, "name": "Rachin Ravindra", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 221, "name": "Azmatullah Omarzai", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 222, "name": "Kamindu Mendis", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 223, "name": "Rovman Powell", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 224, "name": "Mitchell Owen", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 225, "name": "Matthew Short", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 226, "name": "Zea Faulkes", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 227, "name": "Jason Holder", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 228, "name": "Wanindu Hasaranga", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 229, "name": "Cooper Connolly", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 230, "name": "Ben Dwarshuis", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 231, "name": "Jack Edwards", "role": "Allrounder", "nat": "Foreign", "base": 0.5},
    {"id": 232, "name": "Eshan Malinga", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 233, "name": "Corbin Bosch", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 234, "name": "Xavier Bartlett", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 235, "name": "Lockie Ferguson", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 236, "name": "Dushmantha Chameera", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 237, "name": "Kwena Maphaka", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 238, "name": "Nandre Burger", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 239, "name": "Allah Ghazanfar", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 240, "name": "Lhuan-dre Pretorius", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 241, "name": "Nuwan Thushara", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 242, "name": "Brydon Carse", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 243, "name": "Mustafizur Rahman", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 244, "name": "Matt Henry", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 245, "name": "Lungi Ngidi", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 246, "name": "Kyle Jamieson", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 247, "name": "Luke Wood", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 248, "name": "Anrich Nortje", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 249, "name": "Adam Milne", "role": "Bowler", "nat": "Foreign", "base": 0.5},
    {"id": 250, "name": "Jacob Duffy", "role": "Bowler", "nat": "Foreign", "base": 0.5},
]

# --- DATABASE MANAGER ---
def get_db_connection():
    return psycopg2.connect(DB_URI)

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS auction_states (chat_id BIGINT PRIMARY KEY, data TEXT);")
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"DB Error: {e}")

def save_state(chat_id, data_dict):
    conn = get_db_connection(); cur = conn.cursor()
    json_data = json.dumps(data_dict)
    cur.execute("INSERT INTO auction_states (chat_id, data) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET data = %s", (chat_id, json_data, json_data))
    conn.commit(); cur.close(); conn.close()

def load_state(chat_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT data FROM auction_states WHERE chat_id = %s", (chat_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    return json.loads(row[0]) if row else None

# --- HELPER: CHECK IF USER IS TELEGRAM ADMIN ---
async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except: return False

def check_rules(team_data, new_player):
    squad = team_data['squad']
    if len(squad) >= MAX_SQUAD_SIZE: return False, f"Squad full! Max {MAX_SQUAD_SIZE} players."
    curr_for = sum(1 for p in squad if p['nat'] == 'Foreign')
    if new_player['nat'] == 'Foreign' and curr_for >= MAX_FOREIGNERS: return False, f"Foreigner limit ({MAX_FOREIGNERS}) reached!"
    return True, ""

def get_team_stats(squad):
    wk = sum(1 for p in squad if p['role'] == 'Wicketkeeper')
    bowl = sum(1 for p in squad if p['role'] in ['Bowler', 'Allrounder'])
    return wk, bowl

# --- COMMANDS ---

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
🏆 **IPL Auction Bot Commands**

**For Admins:**
/start_auction - Start Session
/pause_auction - Pause bidding
/resume_auction - Resume bidding
/end_auction - Clear all data
/add_owner <Name> - Reply to user to add
/new_player - Bring random player
/player <ID/Name> - Bring specific player
/sold - Finalize current sale

**For Owners:**
/bid <amount> - Place your bid
/purse - Check budgets
/unsold_players - List of passed players
    """
    await update.message.reply_text(msg, parse_mode="Markdown")

async def start_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context): return
    chat_id = update.effective_chat.id
    if load_state(chat_id):
        await update.message.reply_text("⚠ Auction is already active!")
        return
    state = {
        "status": "IDLE",
        "teams": {},
        "unsold": MASTER_PLAYER_LIST.copy(),
        "passed_players": [],
        "current_player": None,
        "current_bid": 0,
        "highest_bidder": None
    }
    save_state(chat_id, state)
    await update.message.reply_text("🚀 **Auction Session Initialized**\nPurse Limit: 120 Cr\nAny Group Admin can now manage the auction.")

async def control_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context): return
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state: return
    
    cmd = update.message.text
    if "/pause" in cmd: state['status'] = "PAUSED"; msg = "⏸ Bidding Paused."
    elif "/resume" in cmd: state['status'] = "BIDDING" if state['current_player'] else "IDLE"; msg = "▶ Bidding Resumed."
    elif "/end" in cmd:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM auction_states WHERE chat_id = %s", (chat_id,))
        conn.commit(); await update.message.reply_text("🛑 Auction Terminated. Data wiped."); return 

    save_state(chat_id, state)
    await update.message.reply_text(msg)

async def add_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context): return
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state: return
    try:
        team_name = context.args[0]
        target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
        if not target: 
             await update.message.reply_text("Reply to a user to make them owner.")
             return
        
        for t_name, t_data in state['teams'].items():
            if t_data['owner_id'] == target.id:
                await update.message.reply_text(f"🚫 User already owns **{t_name}**!")
                return

        state['teams'][team_name] = {"owner_id": target.id, "owner_name": target.first_name, "spent": 0.0, "squad": []}
        save_state(chat_id, state)
        await update.message.reply_text(f"✅ Team **{team_name}** assigned to **{target.first_name}**")
    except: await update.message.reply_text("Usage: /add_owner <TeamName> (Reply to user)")

async def bring_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context): return
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state: return

    cmd = update.message.text
    player = None
    if "/new_player" in cmd:
        if not state['unsold']: 
            await update.message.reply_text("No more players in unsold list!")
            return
        player = random.choice(state['unsold'])
    elif "/player" in cmd:
        query = " ".join(context.args).lower()
        player = next((p for p in state['unsold'] if str(p['id']) == query or p['name'].lower() == query), None)
        if not player:
            player = next((p for p in state['passed_players'] if str(p['id']) == query or p['name'].lower() == query), None)
            if player: state['passed_players'] = [p for p in state['passed_players'] if p['id'] != player['id']]

    if player:
        state['current_player'] = player
        state['current_bid'] = player['base']
        state['highest_bidder'] = None
        state['status'] = "BIDDING"
        state['unsold'] = [p for p in state['unsold'] if p['id'] != player['id']]
        save_state(chat_id, state)
        await update.message.reply_text(f"🏏 **AUCTIONING**: {player['name']}\nRole: {player['role']} | Nat: {player['nat']} | Base: {player['base']} Cr")

async def bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state or state['status'] != "BIDDING": return

    user_id = update.effective_user.id
    team_name = next((n for n, t in state['teams'].items() if t['owner_id'] == user_id), None)
    if not team_name: return

    try:
        amount = float(context.args[0])
        team_data = state['teams'][team_name]
        if amount > (PURSE_LIMIT - team_data['spent']): return
        if amount <= state['current_bid']: return
        
        allowed, reason = check_rules(team_data, state['current_player'])
        if not allowed:
            await update.message.reply_text(f"🚫 {reason}")
            return

        state['current_bid'] = amount
        state['highest_bidder'] = team_name
        save_state(chat_id, state)
        await update.message.reply_text(f"💰 {team_name} bids {amount} Cr")
    except: pass

async def sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context): return
    state = load_state(update.effective_chat.id)
    if not state or not state['current_player']: return

    winner = state['highest_bidder']
    player = state['current_player']
    if not winner:
        state['passed_players'].append(player)
        await update.message.reply_text(f"❌ {player['name']} remains UNSOLD.")
    else:
        price = state['current_bid']
        player['sold_price'] = price
        state['teams'][winner]['spent'] += price
        state['teams'][winner]['squad'].append(player)
        
        wk, bowl = get_team_stats(state['teams'][winner]['squad'])
        warn = ""
        if len(state['teams'][winner]['squad']) == MAX_SQUAD_SIZE:
            if wk < MIN_WICKETKEEPERS: warn += "\n⚠ Notice: Min 1 WK rule not met."
            if bowl < MIN_BOWLING_OPTIONS: warn += f"\n⚠ Notice: Only {bowl}/6 bowling options."
            
        await update.message.reply_text(f"🔨 **SOLD!** {player['name']} to {winner} for {price} Cr!{warn}")

    state['current_player'] = None
    state['status'] = "IDLE"
    save_state(update.effective_chat.id, state)

async def unsold_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state(update.effective_chat.id)
    if not state or not state['passed_players']:
        await update.message.reply_text("No players currently in the unsold pool.")
        return
    msg = "📋 **UNSOLD LIST**\n" + "\n".join([f"• {p['name']} ({p['id']})" for p in state['passed_players']])
    await update.message.reply_text(msg)

async def view_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state(update.effective_chat.id)
    if not state: return
    msg = "💰 **PURSE STATUS**\n"
    for t_name, t_data in state['teams'].items():
        rem = PURSE_LIMIT - t_data['spent']
        msg += f"• **{t_name}**: {rem:.2f} Cr | Squad: {len(t_data['squad'])}/15\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- FLASK ---
app = Flask(__name__)
@app.route('/')
def home(): return "IPL Bot Online"

if __name__ == '__main__':
    init_db()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000))), daemon=True).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start_auction", start_auction))
    bot.add_handler(CommandHandler("pause_auction", control_auction))
    bot.add_handler(CommandHandler("resume_auction", control_auction))
    bot.add_handler(CommandHandler("end_auction", control_auction))
    bot.add_handler(CommandHandler("add_owner", add_owner))
    bot.add_handler(CommandHandler("new_player", bring_player))
    bot.add_handler(CommandHandler("player", bring_player))
    bot.add_handler(CommandHandler("bid", bid))
    bot.add_handler(CommandHandler("sold", sold))
    bot.add_handler(CommandHandler("unsold_players", unsold_players))
    bot.add_handler(CommandHandler("purse", view_info))
    bot.add_handler(CommandHandler("help", help_command))
    bot.run_polling()
