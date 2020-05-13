import os

from flask import Flask, session,render_template,request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
import datetime
from datetime import datetime
import csv
import os
from flask import jsonify
app = Flask(__name__)
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "SsvN2BbKHNPZIbTFfeZxg", "isbns": "0385755880"})
#print(res.json())

@app.route("/",methods=['GET','POST'])
def index():
    return render_template("login.html")


@app.route('/loggedin',methods=['GET','POST'])
def loggedin():
    if request.method =='POST':
        data = request.form
        name = data['uname']
        password = data['psw']

        get_info = db.execute("SELECT * FROM registered WHERE name= :name AND password= :password",
        {"name":name,"password":password}).fetchall()

        db.commit()
       
        #for info in get_info:
        try:
            info=get_info[0]
            flag= True
            
            #print(info.name,type(info.name))
            now = datetime.now()
            login_time = now.strftime("%d/%m/%Y %H:%M:%S")
            db.execute("INSERT INTO login_now (name,login_time) VALUES(:name, :login_now)",
            {"name":info.name,"login_now":login_time})
            db.commit()
            #return("Login Successfull as "+info.name+"!")
            return render_template("home.html",name=info.name)

        except Exception as e:
            return "WRONG USERNAME OR PASSWORD!"
    
@app.route('/signup',methods=['GET','POST'])
def signup():
    now = datetime.now()
    reg_on = now.strftime("%d/%m/%Y %H:%M:%S")
    if request.method== 'POST':
        data1= request.form
        email=data1['uemail']
        name = data1['uname']
        password = data1['psw']
        repassword = data1['repsw']
        get_same_name= db.execute("SELECT * from registered WHERE name=:name",
        {"name":name}).fetchall()
        db.commit()
        try:
            if len(get_same_name) !=0:
                return "name already exists"
            else:
                if password != repassword:
                    return "password didn't match!"
                else:
                    db.execute("INSERT INTO registered (name,password,email,registered_on) VALUES (:name, :password, :email,:registered_on)",
                    {"name":name, "password":password,"email":email,"registered_on":reg_on})

                    db.commit()
                    return "Registration Succesfull!"
        except Exception as e:
            import re 
            find_email_error= re.findall('registered_email_key',str(e))
            find_name_error=re.findall('registered_name_key',str(e))
            #print(find_email_error,"ema")
            #print(find_name_error,"nam")
            if len(find_email_error)!= 0:
                return "Email Already Registered!"
            else:
                return str(e)
            if len(find_name_error)!= 0:
                return "Username Already Registered!"
            else:
                return str(e)
    return render_template("signup.html")

@app.route('/search',methods=["POST"])
def search():
    s_data = request.form
    isbn = s_data['isbn']
    title = s_data['title']
    author = s_data['author']

    #print(isbn,title,author)
    try:
        if db.execute("SELECT isbn,title,author,year from books_record WHERE isbn = :isbn OR title=:title OR author=:author ",{"isbn":isbn,"title":title,"author":author}).rowcount == 0:

            return "No RESULT FOUND!"
        else:
            sel_book = db.execute("SELECT * from books_record WHERE isbn = :isbn OR title=:title OR author=:author ",
                    {"isbn":isbn,"title":title,"author":author}).fetchall()
            
    except Exception as e:
        return (f'VALUE DOES NOT MATCHED {e}')
    

    print(sel_book)

    return render_template("books_list.html",sel_book=sel_book)

@app.route("/spec_book/<int:book_id>")
def spec_book(book_id):

    search_by_id = db.execute("SELECT * from books_record WHERE id=:id",{'id':book_id}).fetchone()

    #temp_list = list(search_by_id[0])
    limit=[1,2,3,4,5]
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "SsvN2BbKHNPZIbTFfeZxg", "isbns": search_by_id.isbn})
    gr_book = res.json()

    #extract_m = gr_book['book']

    for key in gr_book.items():
        for j in key:
            temp_dict = j[0]
    print(temp_dict['work_ratings_count'])
    work_ratings_count = temp_dict['work_ratings_count']
    average_rating = temp_dict['average_rating']
    
    #print(res.json())

    return render_template('book_info.html', record = search_by_id, limits=limit,work_ratings_count=work_ratings_count,average_rating=average_rating)

@app.route("/review/<string:isbn>",methods=["POST"])
def review(isbn):

    review_data = request.form
    review = review_data['txtreview']
    
    rating_no = int(review_data['ratings'])
    recent_login = db.execute("SELECT name FROM  login_now where id = (SELECT max(id) from login_now)").fetchone()
    username = recent_login.name

    if db.execute("SELECT * from reviews where isbn = :isbn AND username = :username",{'isbn':isbn,'username':username}).rowcount == 0:

        db.execute("INSERT INTO reviews (username,review,ratings,isbn) VALUES(:username,:review,:ratings,:isbn)",
        {'username':username,'review':review,'ratings':rating_no,'isbn':isbn})
        db.commit()
        return "Thanks for your review!"
    else:
        return "you already submitted review for this book"

@app.route("/api/<string:book_isbn>")
def books_api(book_isbn):
    if db.execute("SELECT * from books_record WHERE isbn=:isbn ",{"isbn":book_isbn}).rowcount == 0:
        return "INVALID ISBN!"
    else:
        sel_api_book = db.execute("SELECT * from books_record WHERE isbn=:isbn ",
                        {"isbn":book_isbn}).fetchone()
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "SsvN2BbKHNPZIbTFfeZxg", "isbns": sel_api_book.isbn})
        gr_book = res.json()

        #extract_m = gr_book['book']

        for key in gr_book.items():
            for j in key:
                temp_dict = j[0]
        #print(temp_dict['work_ratings_count'])
        work_ratings_count = temp_dict['work_ratings_count']
        average_rating = temp_dict['average_rating']

        #return (str(sel_api_book))
        return jsonify({
            
            "title":sel_api_book.title,
            "author":sel_api_book.author,
            "year":sel_api_book.year,
            "isbn":sel_api_book.isbn,
            "work_ratings_count":work_ratings_count,
            "average_rating":average_rating,
        })
