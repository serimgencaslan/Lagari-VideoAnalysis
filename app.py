# app.py
import os
from functools import wraps
from time import time
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, Response, jsonify, flash
)
from camera import VideoCamera, mjpeg_generator, latest_counts
from db import (
    init_db, close_db,
    log_detection, get_recent_detections,
    verify_user, get_all_users, create_user,
    get_user_by_id, update_user, delete_user
)

from sqlite3 import OperationalError


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = "dev-secret-key"

    # Başlangıçta kamera yok, dashboard'dan seçilecek
    app.camera = None

    # DB init
    with app.app_context():
        init_db()

    app.teardown_appcontext(close_db)

    # ---------- Decorator'lar ----------

    def login_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapper

    def admin_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user or user.get("role") != "admin":
                flash("Bu sayfaya erişmek için admin yetkisi gerekli.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper

    # ---------- Auth Routes ----------

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            row = verify_user(username, password)
            if row:
                session["user"] = {
                    "id": row["id"],
                    "username": row["username"],
                    "role": row["role"],
                }
                return redirect(url_for("dashboard"))
            else:
                error = "Kullanıcı adı veya şifre hatalı."
        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        session.pop("user", None)
        return redirect(url_for("login"))

    # ---------- Dashboard & Stream ----------

    @app.route("/")
    @login_required
    def dashboard():
        stream_error = session.pop("stream_error", None)
        camera_config = session.get("camera_config", {
            "source_type": "video",
            "video_path": "people.mp4",
            "camera_index": 0,
            "detect_people": True,
            "detect_vehicles": False,
        })
        return render_template(
            "dashboard.html",
            stream_error=stream_error,
            camera_config=camera_config,
        )

    @app.route("/configure_stream", methods=["POST"])
    @login_required
    def configure_stream():
        source_type = request.form.get("source_type", "video")
        video_path = request.form.get("video_path", "").strip() or "people.mp4"
        camera_index_raw = request.form.get("camera_index", "0")
        detect_people = request.form.get("detect_people") == "on"
        detect_vehicles = request.form.get("detect_vehicles") == "on"

        try:
            if source_type == "camera":
                camera_index = int(camera_index_raw)
                camera = VideoCamera(source=camera_index)
            else:
                camera = VideoCamera(source=video_path)

            camera.detect_people = detect_people
            camera.detect_vehicles = detect_vehicles

            if hasattr(app, "camera") and app.camera is not None:
                del app.camera

            app.camera = camera
            session["stream_error"] = None
        except Exception as e:
            session["stream_error"] = f"Video / kamera açılamadı: {e}"
            app.camera = None

        session["camera_config"] = {
            "source_type": source_type,
            "video_path": video_path,
            "camera_index": camera_index_raw,
            "detect_people": detect_people,
            "detect_vehicles": detect_vehicles,
        }

        return redirect(url_for("dashboard"))

    @app.route("/video_feed")
    @login_required
    def video_feed():
        if app.camera is None:
            return Response(
                "Stream yok. Lütfen önce bir kaynak seçin.",
                mimetype="text/plain",
                status=503,
            )
        return Response(
            mjpeg_generator(app.camera),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    _last_log_ts = {"value": 0.0}

    @app.route("/api/stats")
    @login_required
    def api_stats():
        if app.camera is None:
            return jsonify(
                {
                    "person_count": 0,
                    "vehicle_count": 0,
                    "alarm": "Video / kamera kaynağı aktif değil.",
                }
            )

        from camera import latest_counts

        person_count = latest_counts.get("person", 0)
        vehicle_count = latest_counts.get("vehicle", 0)

        alarm_msgs = []
        if person_count >= 5:
            alarm_msgs.append("Kişi sayısı 5 ve üzerinde!")
        if vehicle_count >= 10:
            alarm_msgs.append("Araç sayısı 10 ve üzerinde!")
        alarm = " | ".join(alarm_msgs) if alarm_msgs else None

        now = time()
        if now - _last_log_ts["value"] > 5.0:
            try:
                log_detection(person_count, vehicle_count)
                _last_log_ts["value"] = now
            except OperationalError as e:
                # migration sırasında hata olursa UI'yı kilitlemesin
                print("log_detection error:", e)

        return jsonify(
            {
                "person_count": person_count,
                "vehicle_count": vehicle_count,
                "alarm": alarm,
            }
        )


    @app.route("/api/history")
    @login_required
    def api_history():
        try:
            rows = get_recent_detections(limit=50)
            history = [
                {
                    "ts": r["ts"],
                    "person_count": r["person_count"],
                    "vehicle_count": r["vehicle_count"],
                }
                for r in rows
            ]
        except OperationalError as e:
            print("get_recent_detections error:", e)
            history = []
        return jsonify(history)

    # ---------- Admin: User Management  ----------

    @app.route("/admin/users")
    @login_required
    @admin_required
    def admin_users():
        users = get_all_users()
        return render_template("admin_users.html", users=users)

    @app.route("/admin/users/create", methods=["POST"])
    @login_required
    @admin_required
    def admin_users_create():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "user")
        if not username or not password:
            flash("Kullanıcı adı ve şifre zorunludur.", "error")
        else:
            try:
                create_user(username, password, role)
                flash("Kullanıcı oluşturuldu.", "success")
            except Exception as e:
                flash(f"Kullanıcı oluşturulamadı: {e}", "error")
        return redirect(url_for("admin_users"))

    @app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
    @login_required
    @admin_required
    def admin_users_edit(user_id):
        user = get_user_by_id(user_id)
        if user is None:
            flash("Kullanıcı bulunamadı.", "error")
            return redirect(url_for("admin_users"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip() or None
            role = request.form.get("role", "user")
            if not username:
                flash("Kullanıcı adı boş olamaz.", "error")
            else:
                try:
                    update_user(user_id, username, password, role)
                    flash("Kullanıcı güncellendi.", "success")
                    return redirect(url_for("admin_users"))
                except Exception as e:
                    flash(f"Kullanıcı güncellenemedi: {e}", "error")

        return render_template("admin_user_edit.html", user=user)

    @app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def admin_users_delete(user_id):
        try:
            delete_user(user_id)
            flash("Kullanıcı silindi.", "success")
        except Exception as e:
            flash(f"Kullanıcı silinemedi: {e}", "error")
        return redirect(url_for("admin_users"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        threaded=True,
    )
