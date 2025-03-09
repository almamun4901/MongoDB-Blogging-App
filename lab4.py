#!/usr/bin/env python3
import sys
import re
import configparser
from pymongo import MongoClient
from datetime import datetime, timezone

# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')

# MongoDB connection
mongo_config = config['MongoDB']
client = MongoClient(
    host=mongo_config['host'],
    port=int(mongo_config['port'])
)
db = client[mongo_config['database']]

# Helper functions
def generate_permalink(blogname, title):
    """Generate a permalink from blogname and title"""
    return blogname + '.' + re.sub('[^0-9a-zA-Z]+', '_', title)

# Generating current timestamp
def generate_timestamp():
    """Generate a timestamp"""
    return datetime.now(timezone.utc).isoformat()

#Find a post or comment by permalink
def findingPostComment(blogname, permalink):
    
    post = db[blogname].find_one({"permalink": permalink})
    if post:
        return post, None, None
    for post in db[blogname].find():
        for i, comment in enumerate(post.get('comments', [])):
            if comment.get('permalink') == permalink:
                return post, i, None
            for j, subcomment in enumerate(comment.get('comments', [])):
                if subcomment.get('permalink') == permalink:
                    return post, i, j
    return None, None, None

def posting(parts):
    if len(parts) < 6:
        print("Error: Invalid post command", file=sys.stderr)
        return
    blogname, username, title, body, tags = parts[1:6]
    timestamp = generate_timestamp()
    permalink = generate_permalink(blogname, title)
    post_doc = {
        "title": title,
        "userName": username,
        "timestamp": timestamp,
        "permalink": permalink,
        "body": body,
        "comments": []
    }
    if tags:
        post_doc["tags"] = [tag.strip() for tag in tags.split(',')]
    db[blogname].insert_one(post_doc)

def commenting(parts):
    if len(parts) < 5:
        print("Error: Invalid comment command", file=sys.stderr)
        return
    blogname, parent_permalink, username, comment_body = parts[1:5]
    timestamp = generate_timestamp()
    post, comment_idx, subcomment_idx = findingPostComment(blogname, parent_permalink)

    if not post:
        print(f"Error: Could not find post or comment with permalink {parent_permalink}", file=sys.stderr)
        return
    
    comment_doc = {
        "userName": username, 
        "permalink": timestamp, 
        "comment": comment_body, 
        "comments": []
    }
    if comment_idx is None:
        db[blogname].update_one({"_id": post["_id"]}, {"$push": {"comments": comment_doc}})
    elif subcomment_idx is None:
        db[blogname].update_one({"_id": post["_id"]}, {"$push": {f"comments.{comment_idx}.comments": comment_doc}})
    else:
        print("Error: Cannot add comment to a comment on a comment", file=sys.stderr)

def deleteBlog(parts):
    if len(parts) < 4:
        print("Error: Invalid delete command", file=sys.stderr)
        return
    blogname, permalink, username = parts[1:4]
    timestamp = generate_timestamp()

    post, comment_idx, subcomment_idx = findingPostComment(blogname, permalink)

    if not post:
        print(f"Error: Could not find post or comment with permalink {permalink}", file=sys.stderr)
        return
    deletion_message = f"**deleted by {username}**"

    if comment_idx is None:
        db[blogname].update_one({"_id": post["_id"]}, {"$set": {"body": deletion_message, "timestamp": timestamp}})
    elif subcomment_idx is None:
        db[blogname].update_one({"_id": post["_id"]}, {"$set": {f"comments.{comment_idx}.comment": deletion_message, f"comments.{comment_idx}.timestamp": timestamp}})
    else:
        db[blogname].update_one({"_id": post["_id"]}, {"$set": {f"comments.{comment_idx}.comments.{subcomment_idx}.comment": deletion_message, f"comments.{comment_idx}.comments.{subcomment_idx}.timestamp": timestamp}})

def showBlog(parts):
    if len(parts) < 2:
        print("Error: Invalid show command", file=sys.stderr)
        return
    blogname = parts[1]
    print(f"in {blogname.capitalize()}:")
    for post in db[blogname].find().sort("timestamp", 1):
        print(f"  - - - -\ntitle: {post.get('title', '')}\nuserName: {post.get('userName', '')}\ntimestamp: {post.get('timestamp', '')}\npermalink: {post.get('permalink', '')}\nbody:\n  {post.get('body', '')}\n")
        for comment in post.get('comments', []):
            print(f"    - - - -\n  userName: {comment.get('userName', '')}\n  permalink: {comment.get('permalink', '')}\n  comment:\n    {comment.get('comment', '')}\n")

# Extra Credit
def searchString(parts):
    if len(parts) < 3:
        print("Error: Invalid find command", file=sys.stderr)
        return
    blogname, search_string = parts[1:3]
    print(f"in {blogname.capitalize()}:")
    for post in db[blogname].find({"$or": [{"body": {"$regex": search_string}}, {"tags": search_string}]}):
        print(f"  - - - -\ntitle: {post.get('title', '')}\nuserName: {post.get('userName', '')}\ntimestamp: {post.get('timestamp', '')}\npermalink: {post.get('permalink', '')}\nbody:\n  {post.get('body', '')}\n")

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        parts = re.findall(r'".*?"|\S+', line)
        parts = [p.strip('"') for p in parts]
        command = parts[0].lower()
        if command == "post":
            posting(parts)
        elif command == "comment":
            commenting(parts)
        elif command == "delete":
            deleteBlog(parts)
        elif command == "show":
            showBlog(parts)
        elif command == "find":
            searchString(parts)
        else:
            print(f"Error: Unknown command {command}", file=sys.stderr)

if __name__ == "__main__":
    main()

