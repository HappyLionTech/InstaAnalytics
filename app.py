from flask import Flask, request, jsonify
from instaloader import Instaloader, Profile
from itertools import islice
import os

# Directory and file path for the session
SESSION_DIR = "/tmp"  # Change to a persistent location if needed
SESSION_FILE = os.path.join(SESSION_DIR, f"session-{os.getenv('INSTAGRAM_USERNAME')}")

app = Flask(__name__)

# Helper function to format large numbers
def format_count(count):
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)

@app.route('/calculate', methods=['POST'])
def calculate_engagement_and_averages():
    try:
        data = request.json
        profile_username = data.get("username")
        post_limit = data.get("post_limit", 25)

        # Instagram credentials
        ig_username = os.getenv("INSTAGRAM_USERNAME")
        ig_password = os.getenv("INSTAGRAM_PASSWORD")

        if not ig_username or not ig_password:
            return jsonify({"error": "Instagram credentials not set"}), 500

        # Ensure session directory exists
        os.makedirs(SESSION_DIR, exist_ok=True)

        # Initialize Instaloader
        loader = Instaloader(download_pictures=False, download_videos=False, download_video_thumbnails=False)

        # Load or create session
        try:
            loader.load_session_from_file(SESSION_FILE)
        except FileNotFoundError:
            loader.login(ig_username, ig_password)
            loader.save_session_to_file(SESSION_FILE)

        # Fetch profile and calculate metrics
        profile = Profile.from_username(loader.context, profile_username)
        num_followers = profile.followers
        formatted_followers = format_count(num_followers)

        total_likes, total_comments, processed_posts = 0, 0, 0
        for post in islice(profile.get_posts(), post_limit):
            try:
                total_likes += post.likes
                total_comments += post.comments
                processed_posts += 1
            except Exception:
                continue

        if processed_posts > 0:
            avg_likes = total_likes / processed_posts
            avg_comments = total_comments / processed_posts
            engagement_rate = (total_likes + total_comments) / (num_followers * processed_posts) if num_followers > 0 else 0
            reach_multiplier = 1.5
            estimated_reach = (engagement_rate * num_followers) * reach_multiplier

            return jsonify({
                "followers": formatted_followers,
                "average_likes": format_count(avg_likes),
                "average_comments": format_count(avg_comments),
                "engagement_rate": f"{engagement_rate * 100:.2f}%",
                "estimated_reach": format_count(estimated_reach)
            })
        else:
            return jsonify({"error": "No posts processed"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8080)
