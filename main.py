# app.py
import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.distance import geodesic

st.set_page_config(page_title="inDrive Hackathon", layout="wide")



# ======================================================
# Меню
# ======================================================
page = st.sidebar.radio("Меню", [
    "🚕 Симуляция поездки",
    "🔥 Горячие зоны",
    "📲 Рекомендации водителям",
    "📈 Аналитика спроса",
    "🚨 Аномалии"
])

# ======================================================
# 🚕 Симуляция поездки (с прогрессом и длиной маршрута)
# ======================================================
if page == "🚕 Симуляция поездки":
    st.subheader("🚕 Симуляция заказа поездки")
    try:
        df = pd.read_csv("data/clean_trips.csv")[["randomized_id", "latitude", "longitude", "timestamp"]]

        if "current_trip" not in st.session_state:
            if st.button("🚕 Заказать поездку"):
                trip_id = df["randomized_id"].sample(1).iloc[0]
                trip = df[df["randomized_id"] == trip_id].reset_index(drop=True)
                st.session_state.current_trip = trip
                st.session_state.step = 1
                st.session_state.trip_id = trip_id
                st.success("✅ Водитель назначен, поездка началась!")
            else:
                st.info("Нажми кнопку, чтобы заказать поездку 🚕")

        if "current_trip" in st.session_state:
            trip = st.session_state.current_trip
            trip_id = st.session_state.trip_id

            speed = st.slider("⚡ Скорость анимации (мс)", 200, 2000, 700, step=100)
            st.write(f"**🆔 ID поездки:** `{trip_id}`")

            import time
            progress = st.progress(0, text="🚖 Поездка выполняется...")
            chart_placeholder = st.empty()

            for step in range(st.session_state.step, len(trip) + 1):
                st.session_state.step = step
                df_step = trip.iloc[:step]

                percent = int((step / len(trip)) * 100)
                progress.progress(percent, text=f"🚖 Поездка выполняется... {percent}%")

                start_layer = pdk.Layer(
                    "ScatterplotLayer",
                    trip.iloc[[0]],
                    get_position=["longitude", "latitude"],
                    get_color=[0, 255, 0],
                    get_radius=120,
                )
                end_layer = pdk.Layer(
                    "ScatterplotLayer",
                    trip.iloc[[-1]],
                    get_position=["longitude", "latitude"],
                    get_color=[255, 0, 0],
                    get_radius=120,
                )
                route_layer = pdk.Layer(
                    "PathLayer",
                    [{"path": df_step[["longitude", "latitude"]].values.tolist()}],
                    get_path="path",
                    get_color=[255, 0, 0],
                    width_scale=20,
                    width_min_pixels=2,
                )
                car_layer = pdk.Layer(
                    "ScatterplotLayer",
                    df_step.tail(1),
                    get_position=["longitude", "latitude"],
                    get_color=[0, 150, 255],
                    get_radius=100,
                    pickable=True,
                )

                view_state = pdk.ViewState(
                    latitude=df_step["latitude"].mean(),
                    longitude=df_step["longitude"].mean(),
                    zoom=13,
                    pitch=40,
                )

                chart = pdk.Deck(
                    layers=[route_layer, start_layer, end_layer, car_layer],
                    initial_view_state=view_state,
                    tooltip={"text": "🚖 Машина\nШирота: {latitude}\nДолгота: {longitude}\n🕒 Время: {timestamp}"}
                )
                chart_placeholder.pydeck_chart(chart)
                time.sleep(speed / 1000.0)

            # Длина маршрута
            total_distance = 0.0
            for i in range(1, len(trip)):
                p1 = (trip.iloc[i-1]["latitude"], trip.iloc[i-1]["longitude"])
                p2 = (trip.iloc[i]["latitude"], trip.iloc[i]["longitude"])
                total_distance += geodesic(p1, p2).km

            progress.progress(100, text="🏁 Поездка завершена!")
            st.success(f"✅ Поездка `{trip_id}` завершена 🎉")
            st.write(f"📏 Общая длина маршрута: **{total_distance:.2f} км**")

            if st.button("🔄 Новая поездка"):
                for k in ["current_trip", "step", "trip_id"]:
                    st.session_state.pop(k, None)

    except FileNotFoundError:
        st.error("❌ clean_trips.csv не найден. Сначала запусти etl/clean_data.py")

# ======================================================
# 🔥 Горячие зоны (heatmap по агрегациям)
# ======================================================
elif page == "🔥 Горячие зоны":
    st.subheader("🔥 Горячие зоны (heatmap)")
    try:
        df = pd.read_csv("data/agg_trips.csv")
        layer = pdk.Layer(
            "HeatmapLayer",
            df,
            get_position=["lon_grid", "lat_grid"],
            get_weight="count_trips",
            radius_pixels=40,
        )
        view_state = pdk.ViewState(latitude=51.15, longitude=71.42, zoom=11)
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
    except FileNotFoundError:
        st.error("❌ agg_trips.csv не найден. Сначала запусти etl/aggregate_trips.py")


# ======================================================
# 📲 Рекомендации водителям
# ======================================================
elif page == "📲 Рекомендации водителям":
    st.subheader("📲 Оптимальное распределение водителей")
    try:
        df_assign = pd.read_csv("data/assignments.csv")

        drivers_layer = pdk.Layer(
            "ScatterplotLayer",
            df_assign,
            get_position=["driver_lng", "driver_lat"],
            get_color=[0, 150, 255, 200],
            get_radius=80,
            pickable=True,
        )
        zones_layer = pdk.Layer(
            "ScatterplotLayer",
            df_assign,
            get_position=["zone_lng", "zone_lat"],
            get_color=[255, 0, 100, 200],
            get_radius=120,
            pickable=True,
        )

        lines_df = pd.DataFrame([{
            "from_lon": r["driver_lng"], "from_lat": r["driver_lat"],
            "to_lon": r["zone_lng"], "to_lat": r["zone_lat"],
            "zone_predicted": r["zone_predicted"], "distance_km": r["distance_km"]
        } for _, r in df_assign.iterrows()])

        lines_layer = pdk.Layer(
            "LineLayer",
            lines_df,
            get_source_position=["from_lon", "from_lat"],
            get_target_position=["to_lon", "to_lat"],
            get_color=[200, 200, 200, 150],
            get_width=2,
            pickable=True,
        )

        view_state = pdk.ViewState(latitude=51.15, longitude=71.42, zoom=11, pitch=40)
        st.pydeck_chart(pdk.Deck(
            layers=[drivers_layer, zones_layer, lines_layer],
            initial_view_state=view_state,
            tooltip={"text": "🚖 Водитель → Зона\n📏 Дистанция: {distance_km}\n📈 Прогноз: {zone_predicted}"}
        ))
        st.markdown("### 📋 Таблица распределения")
        st.dataframe(df_assign)

    except FileNotFoundError:
        st.error("❌ assignments.csv не найден. Сначала запусти etl/visualize.py")

# ======================================================
# 📈 Аналитика спроса
# ======================================================
elif page == "📈 Аналитика спроса":
    st.subheader("📈 Аналитический инструмент: Факт vs Прогноз + Будни vs Выходные + What-if")

    # ---------- Факт vs Прогноз ----------
    try:
        df_fact = pd.read_csv("data/aggregates.csv")
        df_pred = pd.read_csv("data/predictions.csv")

        hour = st.slider("⏰ Час", int(df_fact["hour"].min()), int(df_fact["hour"].max()), int(df_fact["hour"].min()))
        day_map = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day = st.selectbox("📅 День недели", day_map)
        day_num = day_map.index(day)

        fact_filtered = df_fact[(df_fact["hour"] == hour) & (df_fact["dayofweek"] == day_num)].copy()
        pred_filtered = df_pred[(df_pred["hour"] == hour) & (df_pred["dayofweek"] == day_num)].copy()

        # подготовка цветов и высоты (ФАКТ)
        if not fact_filtered.empty:
            fact_filtered["count_trips"] = pd.to_numeric(fact_filtered["count_trips"], errors="coerce").fillna(0).clip(lower=0)
            max_c = max(1.0, fact_filtered["count_trips"].max())
            c_norm = (fact_filtered["count_trips"] / max_c * 255).round().clip(0, 255).astype(int)
            fact_filtered["color"] = c_norm.apply(lambda v: [int(v), 50, 150, 200])

        # подготовка цветов и высоты (ПРОГНОЗ)
        if not pred_filtered.empty:
            pred_filtered["predicted"] = pd.to_numeric(pred_filtered["predicted"], errors="coerce").fillna(0).clip(lower=0)
            max_p = max(1.0, pred_filtered["predicted"].max())
            p_norm = (pred_filtered["predicted"] / max_p * 255).round().clip(0, 255).astype(int)
            pred_filtered["color"] = p_norm.apply(lambda v: [int(v), 120, 200, 180])

        st.write("📊 Факт:", len(fact_filtered), "точек | 📈 Прогноз:", len(pred_filtered), "точек")

        col1, col2 = st.columns(2)
        with col1:
            st.write("📊 Факт")
            if not fact_filtered.empty:
                fact_layer = pdk.Layer(
                    "H3HexagonLayer",
                    fact_filtered,
                    get_hexagon="h3",
                    get_fill_color="color",
                    extruded=True,
                    get_elevation="count_trips",
                    elevation_scale=2,
                    pickable=True,
                )
                st.pydeck_chart(pdk.Deck(
                    layers=[fact_layer],
                    initial_view_state=pdk.ViewState(latitude=51.15, longitude=71.42, zoom=11, pitch=40),
                    tooltip={"text": "🗺️ H3: {h3}\n📊 Факт: {count_trips}"}
                ))
            else:
                st.warning("⚠️ Нет фактических данных для выбранного часа/дня.")

        with col2:
            st.write("📈 Прогноз")
            if not pred_filtered.empty:
                pred_layer = pdk.Layer(
                    "H3HexagonLayer",
                    pred_filtered,
                    get_hexagon="h3",
                    get_fill_color="color",
                    extruded=True,
                    get_elevation="predicted",
                    elevation_scale=2,
                    pickable=True,
                )
                st.pydeck_chart(pdk.Deck(
                    layers=[pred_layer],
                    initial_view_state=pdk.ViewState(latitude=51.15, longitude=71.42, zoom=11, pitch=40),
                    tooltip={"text": "🗺️ H3: {h3}\n📈 Прогноз: {predicted}"}
                ))
            else:
                st.warning("⚠️ Нет прогноза для выбранного часа/дня.")

        # Метрики
        if not fact_filtered.empty and not pred_filtered.empty:
            merged = pd.merge(
                fact_filtered[["h3", "count_trips"]],
                pred_filtered[["h3", "predicted"]],
                on="h3", how="inner"
            )
            if not merged.empty:
                merged["abs_err"] = (merged["count_trips"] - merged["predicted"]).abs()
                mae = merged["abs_err"].mean()
                merged["perc_err"] = merged["abs_err"] / merged["count_trips"].replace(0, 1)
                mape = merged["perc_err"].mean() * 100
                st.write(f"**MAE:** {mae:.2f} | **MAPE:** {mape:.1f}%")
                st.bar_chart(merged[["count_trips", "predicted"]].reset_index(drop=True))

    except FileNotFoundError:
        st.error("❌ Нет данных для Факт vs Прогноз")

    # ---------- Будни vs Выходные ----------
    st.markdown("## 📊 Будни vs Выходные")
    try:
        df = pd.read_csv("data/agg_trips.csv")
        df["day_type"] = df["day_of_week"].apply(lambda x: "Будни" if x < 5 else "Выходные")
        hourly = df.groupby(["day_type", "hour"])["count_trips"].mean().reset_index()
        c1, c2 = st.columns(2)
        with c1:
            st.line_chart(hourly[hourly["day_type"] == "Будни"].set_index("hour")["count_trips"])
            st.caption("📈 Будни")
        with c2:
            st.line_chart(hourly[hourly["day_type"] == "Выходные"].set_index("hour")["count_trips"])
            st.caption("📉 Выходные")
    except FileNotFoundError:
        st.error("❌ Нет данных для Будни vs Выходные")

    # ---------- What-if ----------
    st.markdown("## 🤔 What-if сценарий")
    try:
        df = pd.read_csv("data/agg_trips.csv")
        base_hour = st.slider("⏰ Час для сценария", 0, 23, 18, key="whatif_hour")
        increase = st.slider("📈 Рост спроса (%)", -50, 200, 50, key="whatif_increase")

        base_data = df[df["hour"] == base_hour].copy()
        base_data["scenario_trips"] = base_data["count_trips"] * (1 + increase / 100)

        base_layer = pdk.Layer(
            "ScatterplotLayer",
            base_data,
            get_position=["lon_grid", "lat_grid"],
            get_color=[0, 150, 255, 150],
            get_radius="count_trips",
            pickable=True,
        )
        scenario_layer = pdk.Layer(
            "ScatterplotLayer",
            base_data,
            get_position=["lon_grid", "lat_grid"],
            get_color=[255, 80, 80, 200],
            get_radius="scenario_trips",
            pickable=True,
        )

        view_state = pdk.ViewState(latitude=51.15, longitude=71.42, zoom=11)
        st.pydeck_chart(pdk.Deck(
            layers=[base_layer, scenario_layer],
            initial_view_state=view_state,
            tooltip={"text": "📍 Координаты\nФакт: {count_trips}\nСценарий: {scenario_trips}"}
        ))
    except FileNotFoundError:
        st.error("❌ Нет данных для What-if")

elif page == "🚨 Аномалии":
    st.subheader("🚨 Выявление аномальных поездок")

    try:
        df = pd.read_csv("data/clean_trips.csv")[["randomized_id", "latitude", "longitude", "timestamp", "spd"]]

        # Чтобы не грузить всё (1.2M строк), можно ограничить сверху
        max_rows = st.slider("📊 Сколько строк загрузить (для скорости)", 1000, len(df), 20000, step=1000)
        df = df.head(max_rows)

        # Метрики по каждой поездке
        stats = []
        for trip_id, trip in df.groupby("randomized_id"):
            trip = trip.sort_values("timestamp")
            total_dist = 0.0
            for i in range(1, len(trip)):
                p1 = (trip.iloc[i-1]["latitude"], trip.iloc[i-1]["longitude"])
                p2 = (trip.iloc[i]["latitude"], trip.iloc[i]["longitude"])
                total_dist += geodesic(p1, p2).km

            avg_speed = trip["spd"].mean()
            stats.append({
                "trip_id": trip_id,
                "distance_km": total_dist,
                "avg_speed": avg_speed,
                "n_points": len(trip)
            })

        stats_df = pd.DataFrame(stats)

        # Правила аномалий
        stats_df["is_anomaly"] = (
            (stats_df["distance_km"] > 30) |   # слишком длинная поездка
            (stats_df["avg_speed"] > 120)      # нереальная скорость
        )

        st.success(f"🚨 Найдено {stats_df['is_anomaly'].sum()} аномалий из {len(stats_df)} поездок")

        # Визуализация
        anomaly_paths, normal_paths = [], []
        for trip_id, trip in df.groupby("randomized_id"):
            path = trip[["longitude", "latitude"]].values.tolist()
            if stats_df.loc[stats_df["trip_id"] == trip_id, "is_anomaly"].iloc[0]:
                anomaly_paths.append({"trip_id": trip_id, "path": path})
            else:
                normal_paths.append({"trip_id": trip_id, "path": path})

        normal_layer = pdk.Layer(
            "PathLayer",
            normal_paths,
            get_path="path",
            get_color=[150, 150, 150],
            width_scale=20,
            width_min_pixels=2,
            pickable=True,
        )
        anomaly_layer = pdk.Layer(
            "PathLayer",
            anomaly_paths,
            get_path="path",
            get_color=[255, 0, 0],
            width_scale=30,
            width_min_pixels=3,
            pickable=True,
        )

        view_state = pdk.ViewState(latitude=51.15, longitude=71.42, zoom=11, pitch=30)
        st.pydeck_chart(pdk.Deck(
            layers=[normal_layer, anomaly_layer],
            initial_view_state=view_state,
            tooltip={"text": "🆔 Trip: {trip_id}"}
        ))

        st.markdown("### 📋 Таблица аномальных поездок")
        st.dataframe(stats_df[stats_df["is_anomaly"]])

    except FileNotFoundError:
        st.error("❌ clean_trips.csv не найден")
