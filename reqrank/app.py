from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import io, csv, random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reqrank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ----------------- 数据模型 -----------------
class Requirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(20), default="functional")  # functional / nonfunctional
    moscow = db.Column(db.String(1), default="C")              # M / S / C / W
    business_value = db.Column(db.Integer, default=5)
    time_criticality = db.Column(db.Integer, default=5)
    risk_reduction = db.Column(db.Integer, default=5)
    effort = db.Column(db.Integer, default=5)                  # 1~10
    risk_level = db.Column(db.Integer, default=3)              # 1~5
    assignee = db.Column(db.String(100), default="")
    status = db.Column(db.String(20), default="todo")          # todo / doing / done
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def wsjf(self):
        # 防止除0
        effort = max(1, int(self.effort or 1))
        return (int(self.business_value or 0)
                + int(self.time_criticality or 0)
                + int(self.risk_reduction or 0)) / effort

with app.app_context():
    db.create_all()

# ----------------- 路由 -----------------
@app.route("/")
def index():
    return redirect(url_for("list_requirements"))

@app.route("/requirements")
def list_requirements():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    moscow = request.args.get("moscow", "")
    sort = request.args.get("sort", "")

    query = Requirement.query
    if q:
        query = query.filter(Requirement.title.like(f"%{q}%"))
    if status:
        query = query.filter_by(status=status)
    if moscow:
        query = query.filter_by(moscow=moscow)

    items = query.all()
    if sort == "wsjf":
        items = sorted(items, key=lambda r: r.wsjf, reverse=True)
    elif sort == "created":
        items = sorted(items, key=lambda r: r.created_at, reverse=True)

    return render_template("list.html", items=items, q=q, status=status, moscow=moscow, sort=sort)

@app.route("/requirements/new", methods=["GET", "POST"])
def new_requirement():
    if request.method == "POST":
        f = request.form
        r = Requirement(
            title=f["title"],
            description=f.get("description",""),
            category=f.get("category","functional"),
            moscow=f.get("moscow","C"),
            business_value=int(f.get("business_value",5)),
            time_criticality=int(f.get("time_criticality",5)),
            risk_reduction=int(f.get("risk_reduction",5)),
            effort=max(1, int(f.get("effort",5))),
            risk_level=int(f.get("risk_level",3)),
            assignee=f.get("assignee",""),
            status=f.get("status","todo"),
        )
        db.session.add(r); db.session.commit()
        return redirect(url_for("list_requirements"))
    return render_template("edit.html", item=None)

@app.route("/requirements/<int:id>/edit", methods=["GET", "POST"])
def edit_requirement(id):
    r = Requirement.query.get_or_404(id)
    if request.method == "POST":
        f = request.form
        r.title = f["title"]
        r.description = f.get("description","")
        r.category = f.get("category","functional")
        r.moscow = f.get("moscow","C")
        r.business_value = int(f.get("business_value",5))
        r.time_criticality = int(f.get("time_criticality",5))
        r.risk_reduction = int(f.get("risk_reduction",5))
        r.effort = max(1, int(f.get("effort",5)))
        r.risk_level = int(f.get("risk_level",3))
        r.assignee = f.get("assignee","")
        r.status = f.get("status","todo")
        r.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("list_requirements"))
    return render_template("edit.html", item=r)

@app.route("/requirements/<int:id>/delete", methods=["POST"])
def delete_requirement(id):
    r = Requirement.query.get_or_404(id)
    db.session.delete(r); db.session.commit()
    return redirect(url_for("list_requirements"))

@app.route("/analysis")
def analysis():
    items = Requirement.query.all()
    # Chart.js 数据
    chart_data = [{
        "title": r.title,
        "moscow": r.moscow,
        "effort": r.effort,
        "value_sum": r.business_value + r.time_criticality + r.risk_reduction,
        "risk_level": r.risk_level
    } for r in items]
    m_count = {"M":0,"S":0,"C":0,"W":0}
    for r in items:
        m_count[r.moscow] = m_count.get(r.moscow,0) + 1

    # WSJF 降序
    items_sorted = sorted(items, key=lambda r: r.wsjf, reverse=True)
    return render_template("analysis.html", items=items_sorted, chart_data=chart_data, m_count=m_count)

@app.route("/export/csv")
def export_csv():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    moscow = request.args.get("moscow", "")
    query = Requirement.query
    if q:
        query = query.filter(Requirement.title.like(f"%{q}%"))
    if status:
        query = query.filter_by(status=status)
    if moscow:
        query = query.filter_by(moscow=moscow)
    items = query.all()

    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(["id","title","moscow","business_value","time_criticality",
                "risk_reduction","effort","wsjf","status","assignee"])
    for r in items:
        w.writerow([r.id, r.title, r.moscow, r.business_value, r.time_criticality,
                    r.risk_reduction, r.effort, f"{r.wsjf:.2f}", r.status, r.assignee])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="reqrank.csv")

# ----------- 便捷：一键生成示例数据（演示用，做完可删） -----------
@app.route("/seed")
def seed():
    titles = [
        "登录注册与找回密码","个人资料编辑","搜索功能优化","首页推荐算法",
        "导出CSV","角色与权限（精简）","系统健康检查页","深色模式",
        "通知中心","批量导入需求","看板视图（选做）","PDF导出（选做）",
        "性能监控（非功能）","错误日志（非功能）","备份恢复（非功能）",
        "移动端适配（非功能）","无障碍（非功能）","帮助文档"
    ]
    ms = ["M","S","C","W"]
    people = ["Alice","Bob","Carol","David","Eve","Frank"]
    for t in titles:
        r = Requirement(
            title=t,
            description=f"{t} 的详细描述…",
            category="functional" if "（非功能）" not in t else "nonfunctional",
            moscow=random.choice(ms),
            business_value=random.randint(4,9),
            time_criticality=random.randint(3,9),
            risk_reduction=random.randint(2,8),
            effort=random.randint(1,8),
            risk_level=random.randint(1,5),
            assignee=random.choice(people),
            status=random.choice(["todo","doing","done"])
        )
        db.session.add(r)
    db.session.commit()
    return "Seed OK. 返回 /requirements 查看。"

if __name__ == "__main__":
    app.run(debug=True)
