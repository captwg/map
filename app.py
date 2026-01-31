import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 页面配置
st.set_page_config(page_title="遗传病突变位点全球分布看板", layout="wide")

st.title("🌍 遗传病突变位点全球人群频率分布")

# 加载数据
@st.cache_data
def load_data():
    # 尝试多种可能的文件名（支持压缩格式）
    possible_paths = [
        "final_variant_data.csv",
        "final_variant_data.csv.gz",
        "final_variant_data.zip"
    ]
    
    data_path = None
    for path in possible_paths:
        if os.path.exists(path):
            data_path = path
            break
    
    if data_path is None:
        st.error("找不到变异数据文件。请确保仓库中包含 final_variant_data.csv 或其压缩包 (.gz / .zip)")
        return None
    
    # 加载数据（Pandas 会自动处理 .gz 和 .zip 压缩）
    try:
        df = pd.read_csv(data_path)
        # 确保 rsid 格式正确
        df['rsid'] = pd.to_numeric(df['rsid'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"读取数据文件 {data_path} 时出错: {e}")
        return None

try:
    full_df = load_data()
except Exception as e:
    st.error(f"加载数据时出错: {e}")
    full_df = None

if full_df is not None:
    # 侧边栏：筛选
    st.sidebar.header("🔍 搜索与筛选")
    st.sidebar.info("提示：如果一个变异关联了多种疾病，搜索任一疾病均可找到该变异。")
    
    disease_search = st.sidebar.text_input("1. 搜索遗传病名称 (Phenotype):", "").strip()
    gene_search = st.sidebar.text_input("2. 搜索基因符号 (Gene Symbol):", "").strip()
    
    # 过滤逻辑
    filtered_df = full_df
    if disease_search:
        filtered_df = filtered_df[filtered_df['PhenotypeList'].str.contains(disease_search, case=False, na=False)]
    if gene_search:
        filtered_df = filtered_df[filtered_df['GeneSymbol'].str.contains(gene_search, case=False, na=False)]
    
    st.sidebar.write(f"当前筛选结果: {len(filtered_df)} 条记录")
    
    if not filtered_df.empty:
        st.subheader("📋 匹配的突变与疾病列表")
        display_limit = 500
        display_df = filtered_df.head(display_limit).copy()
        
        display_df['SelectionName'] = display_df['GeneSymbol'].astype(str) + " | " + display_df['Name'].astype(str).str[:40] + "... | 疾病: " + display_df['PhenotypeList'].astype(str).str[:60] + "..."
        
        selected_option = st.selectbox(
            "请选择一个具体的变异条目查看详情:",
            options=display_df['SelectionName'].tolist()
        )
        
        selected_row = display_df[display_df['SelectionName'] == selected_option].iloc[0]
        rsid_val = selected_row['rsid']
        
        # UI 卡片显示详细信息
        with st.container():
            st.markdown("---")
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"### 🧬 变异详情")
                st.write(f"**标准名称:** `{selected_row['Name']}`")
                st.write(f"**关联疾病:** {selected_row['PhenotypeList']}")
            with c2:
                st.markdown(f"### 📊 临床属性")
                st.write(f"**基因:** {selected_row['GeneSymbol']}")
                st.write(f"**RSID:** `rs{int(rsid_val)}`" if pd.notnull(rsid_val) else "**RSID:** N/A")
                st.write(f"**临床意义:** {selected_row['ClinicalSignificance']}")

        # 频率地图部分
        if pd.notnull(rsid_val):
            # 检查是否有任何频率数据
            freq_cols = ['af_afr', 'af_amr', 'af_eas', 'af_nfe', 'af_fin', 'af_sas', 'af_asj', 'af_oth']
            has_freq = any(pd.notnull(selected_row.get(col)) and float(selected_row.get(col)) > 0 for col in freq_cols)
            
            if has_freq:
                # 细化地图分布点，增加更多人群覆盖
                map_data = [
                    {'Region': '非洲 (African)', 'Lat': 0, 'Lon': 20, 'Freq': selected_row.get('af_afr', 0)},
                    {'Region': '美洲 (Latino/Admixed American)', 'Lat': 15, 'Lon': -90, 'Freq': selected_row.get('af_amr', 0)},
                    {'Region': '东亚 (East Asian)', 'Lat': 35, 'Lon': 110, 'Freq': selected_row.get('af_eas', 0)},
                    {'Region': '西欧/北非 (Non-Finnish European)', 'Lat': 48, 'Lon': 5, 'Freq': selected_row.get('af_nfe', 0)},
                    {'Region': '芬兰 (Finnish)', 'Lat': 62, 'Lon': 26, 'Freq': selected_row.get('af_fin', 0)},
                    {'Region': '南亚 (South Asian)', 'Lat': 22, 'Lon': 78, 'Freq': selected_row.get('af_sas', 0)},
                    {'Region': '德系犹太人 (Ashkenazi Jewish)', 'Lat': 32, 'Lon': 35, 'Freq': selected_row.get('af_asj', 0)},
                    {'Region': '其他人群 (Other)', 'Lat': -20, 'Lon': 140, 'Freq': selected_row.get('af_oth', 0)}
                ]
                
                m_df = pd.DataFrame(map_data)
                m_df['Freq'] = pd.to_numeric(m_df['Freq'], errors='coerce').fillna(0)
                valid_m_df = m_df[m_df['Freq'] > 0]
                
                if not valid_m_df.empty:
                    st.subheader("🌍 全球人群频率分布地图")
                    
                    # 使用 Mapbox 或散点地理图
                    fig = px.scatter_geo(
                        valid_m_df, 
                        lat="Lat", 
                        lon="Lon", 
                        size="Freq", 
                        color="Freq",
                        hover_name="Region", 
                        projection="natural earth",
                        color_continuous_scale=px.colors.sequential.YlOrRd,
                        size_max=45,
                        title=f"RSID: rs{int(rsid_val)} 的全球人群分布 (数据源: gnomAD)"
                    )
                    
                    # 优化地图外观
                    fig.update_geos(
                        showcountries=True, countrycolor="Linen",
                        showcoastlines=True, coastlinecolor="LightBlue",
                        showland=True, landcolor="Ivory",
                        showocean=True, oceancolor="LightCyan"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("查看具体人群频率数值 (gnomAD Population Frequencies)"):
                        st.write("注：这些频率代表该突变在特定人群库中的比例。")
                        st.table(m_df[m_df['Freq'] > 0][['Region', 'Freq']])
                else:
                    st.info("ℹ️ 该变异在所有人群库中的频率均低于检测阈值。")
            else:
                st.warning("📊 数据库记录确认：gnomAD 数据库中暂无该位点的频率记录。")
                st.markdown("""
                **为什么没有记录？**
                1. **罕见性**：致病性突变在人群中通常极度罕见。gnomAD 虽然覆盖了 14 万人，但仍可能未捕获到该变异。
                2. **人群偏差**：目前全球公共数据库（如 gnomAD）中欧洲人群占比最高（约 50% 以上），亚洲和美洲人群样本相对较少。
                3. **技术限制**：部分复杂的 Indel 或结构变异在标准测序流程中难以准确计数。
                """)
        else:
            st.warning("此记录缺少 RSID，无法匹配全球频率数据。")

st.sidebar.markdown("---")
st.sidebar.write("💡 **说明**: 看板展示了 ClinVar 致病突变在全球人群中的分布频率。")
