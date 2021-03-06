from flask import abort, current_app
from flask_restful import Resource, fields, marshal_with
from flask_jwt_extended import jwt_required, get_jwt_identity
from webapp.blog.models import db, Post, Tag, Reminder
from webapp.auth.models import User
from .parsers import (
    post_get_parser,
    post_post_parser,
    post_put_parser,
    reminder_post_parser
)
from .fields import HTMLField


nested_tag_fields = {
    'id': fields.Integer(),
    'title': fields.String()
}

post_fields = {
    'id': fields.Integer(),
    'author': fields.String(attribute=lambda x: x.user.username),
    'title': fields.String(),
    'text': HTMLField(),
    'tags': fields.List(fields.Nested(nested_tag_fields)),
    'publish_date': fields.DateTime(dt_format='iso8601')
}

reminder_fields = {
    'id': fields.Integer(),
    'email': fields.String(),
    'text': fields.String(),
}


def add_tags_to_post(post, tags_list):
    for item in tags_list:
        tag = Tag.query.filter_by(title=item).first()

        # Add the tag if it exists. If not, make a new tag
        if tag:
            post.tags.append(tag)
        else:
            new_tag = Tag(item)
            post.tags.append(new_tag)


class ReminderApi(Resource):
    @marshal_with(reminder_fields)
    @jwt_required
    def get(self, reminder_id=None):
        print("CANAS")
        if reminder_id:
            reminder = Reminder.query.get(reminder_id)
            if not reminder:
                abort(404)
            return reminder
        else:
            reminders = Reminder.query.all()
            return reminders

    @jwt_required
    def post(self, reminder_id=None):
        if reminder_id:
            abort(400)
        else:
            args = reminder_post_parser.parse_args(strict=True)
            new_reminder = Reminder()
            new_reminder.email = args['email']
            new_reminder.text = args['text']
            db.session.add(new_reminder)
            db.session.commit()
            return {'id': new_reminder.id}, 201


class PostApi(Resource):
    @marshal_with(post_fields)
    @jwt_required
    def get(self, post_id=None):
        if post_id:
            post = Post.query.get(post_id)
            if not post:
                abort(404)
            return post
        else:
            args = post_get_parser.parse_args()
            page = args['page'] or 1

            if args['user']:
                user = User.query.filter_by(username=args['user']).first()
                if not user:
                    abort(404)

                posts = user.posts.order_by(
                    Post.publish_date.desc()
                ).paginate(page, current_app.config['POSTS_PER_PAGE'])
            else:
                posts = Post.query.order_by(
                    Post.publish_date.desc()
                ).paginate(page, current_app.config['POSTS_PER_PAGE'])

            return posts.items

    @jwt_required
    def post(self, post_id=None):
        if post_id:
            abort(400)
        else:
            args = post_post_parser.parse_args(strict=True)
            new_post = Post(args['title'])
            new_post.user_id = get_jwt_identity()
            new_post.text = args['text']

            if args['tags']:
                add_tags_to_post(new_post, args['tags'])

            db.session.add(new_post)
            db.session.commit()
            return {'id': new_post.id}, 201

    @jwt_required
    def put(self, post_id=None):
        if not post_id:
            abort(400)
        post = Post.query.get(post_id)
        if not post:
            abort(404)
        args = post_put_parser.parse_args(strict=True)
        if get_jwt_identity() != post.user_id:
            abort(403)
        if args['title']:
            post.title = args['title']
        if args['text']:
            post.text = args['text']
        if args['tags']:
            add_tags_to_post(post, args['tags'])

        db.session.add(post)
        db.session.commit()
        return {'id': post.id}, 201

    @jwt_required
    def delete(self, post_id=None):
        if not post_id:
            abort(400)
        post = Post.query.get(post_id)
        if not post:
            abort(404)
        if get_jwt_identity() != post.user_id:
            abort(401)

        db.session.delete(post)
        db.session.commit()
        return "", 204
