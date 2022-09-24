from http.client import UNAUTHORIZED
from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post
from db.models.user import User
from db.utils import row_to_dict
from middlewares import auth_required
from sqlalchemy.orm.exc import UnmappedInstanceError

SORTABLE_PROPERTIES = ["id", "reads", "likes", "popularity"]
SORT_DIRECTIONS = ["asc", "desc"]
UNAUTHORIZED_MESSAGE = "Unathorized Access. Not Logged In"


@api.post("/posts")
@auth_required
def posts():
    # validation
    user = g.get("user")
    if user is None:
        return abort(401, UNAUTHORIZED_MESSAGE)

    data = request.get_json(force=True)
    text = data.get("text", None)
    tags = data.get("tags", None)
    if text is None:
        return jsonify({"error": "Must provide text for the new post"}), 400

    # Create new post
    post_values = {"text": text}
    if tags:
        post_values["tags"] = tags

    post = Post(**post_values)
    db.session.add(post)
    db.session.commit()

    user_post = UserPost(user_id=user.id, post_id=post.id)
    db.session.add(user_post)
    db.session.commit()

    return row_to_dict(post), 200


@api.route("/posts/<int:postId>", methods=["PATCH"])
@auth_required
def update(postId):
    # validation
    user = g.get("user")
    post = Post.query.get(postId)
    authors = UserPost.query.filter(UserPost.post_id == postId).all()
    if user is None:
        return abort(401, UNAUTHORIZED_MESSAGE)

    if post is None:
        return jsonify({"error": "Post not found"}), 404

    if user.id not in [author.user_id for author in authors]:
        return jsonify({"error": "You are not authorized to update this post"}), 403

    # get data
    data = request.get_json(force=True)
    authorIds = data.get("authorIds", None)
    text = data.get("text", None)
    tags = data.get("tags", None)

    # return error for invalid fields
    if authorIds:
        if not isinstance(authorIds, list):
            return jsonify({"error": "Invalid type, authorIds is not an array"}), 400
        try:
            authorIds = [int(elem) for elem in authorIds]
        except Exception as e:
            return jsonify({"error": "Invalid type, non integer in authorIds"}), 400

    if tags and not isinstance(tags, list):
        return jsonify({"error": "Invalid type, tags is not an array"}), 400

    # remove duplicate authorIds
    if authorIds:
        authorIds = list(set(authorIds))

    # update authors and post
    if authorIds:
        currAuthors = UserPost.query.filter(UserPost.post_id == postId)
        # remove authors that are not in authorIds
        currAuthors.filter(UserPost.user_id.notin_(authorIds)).delete()
        # filter and add authors that are not in currAuthors
        authorIds = [
            UserPost(user_id=authorId, post_id=postId) for authorId in authorIds
            if authorId not in [author.user_id for author in currAuthors]]
        db.session.add_all(authorIds)
        db.session.commit()

    if text:
        post.text = text
    if tags:
        post.tags = tags
    db.session.commit()

    # add authors to post
    updatedPost = row_to_dict(post)
    updatedPost["authorIds"] = sorted([author.user_id for author in UserPost.query.filter(
        UserPost.post_id == postId)])

    return jsonify({"post": updatedPost}), 200


@api.get("/posts")
@auth_required
def fetch():
    """
    Fetch all posts for a given author
    """
    # validation
    user = g.get("user")
    if user is None:
        return abort(401, UNAUTHORIZED_MESSAGE)

    # parse query params
    authorIds = request.args.get("authorIds", None).split(",")
    sortBy = request.args.get("sortBy", "id")
    direction = request.args.get("direction", "asc")
    authorIds = [s for s in authorIds if s.isdigit()]
    if(sortBy not in SORTABLE_PROPERTIES):
        return jsonify({"error": "Invalid sortBy parameter"}), 400

    if(direction not in SORT_DIRECTIONS):
        return jsonify({"error": "Invalid direction parameter"}), 400
    # fetch posts
    posts = set()
    for authorId in authorIds:
        try:
            posts.update(Post.get_posts_by_user_id(authorId))
        except UnmappedInstanceError:
            pass

    # sort posts with sorted method
    posts = sorted(posts, key=lambda x: getattr(
                   x, sortBy), reverse=(direction == "desc"))

    return jsonify({'posts': [row_to_dict(post) for post in posts]}), 200
