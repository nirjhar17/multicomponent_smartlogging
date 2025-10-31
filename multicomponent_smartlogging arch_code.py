from PIL import Image, ImageDraw, ImageFont
import math

# Create image - ULTRA HIGH RESOLUTION
width, height = 4800, 2640
img = Image.new('RGB', (width, height), color='#1a1a1a')
draw = ImageDraw.Draw(img)

# Colors
colors = {
    'blue': '#3b82f6',
    'yellow': '#fbbf24',
    'green': '#10b981',
    'purple': '#a78bfa',
    'red': '#ef4444',
    'cyan': '#06b6d4',
    'orange': '#f97316',
    'gray': '#6b7280',
    'bg': '#2a2a2a',
    'text': '#FFFFFF',
    'text_gray': '#9CA3AF'
}

# Fonts - MUCH LARGER for ultra high resolution with bigger content text
try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
    font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
    font_icon = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 80)
    font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", 28)  # Small italic for labels
except:
    font_title = font_large = font_normal = font_small = font_icon = font_label = ImageFont.load_default()

def draw_box(draw, coords, color, title, lines):
    x1, y1, x2, y2 = coords
    radius = 16
    # Fill
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=colors['bg'])
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=colors['bg'])
    draw.pieslice([x1, y1, x1 + radius*2, y1 + radius*2], 180, 270, fill=colors['bg'])
    draw.pieslice([x2 - radius*2, y1, x2, y1 + radius*2], 270, 360, fill=colors['bg'])
    draw.pieslice([x1, y2 - radius*2, x1 + radius*2, y2], 90, 180, fill=colors['bg'])
    draw.pieslice([x2 - radius*2, y2 - radius*2, x2, y2], 0, 90, fill=colors['bg'])
    # Border
    draw.arc([x1, y1, x1 + radius*2, y1 + radius*2], 180, 270, fill=color, width=5)
    draw.arc([x2 - radius*2, y1, x2, y1 + radius*2], 270, 360, fill=color, width=5)
    draw.arc([x1, y2 - radius*2, x1 + radius*2, y2], 90, 180, fill=color, width=5)
    draw.arc([x2 - radius*2, y2 - radius*2, x2, y2], 0, 90, fill=color, width=5)
    draw.line([(x1 + radius, y1), (x2 - radius, y1)], fill=color, width=5)
    draw.line([(x1 + radius, y2), (x2 - radius, y2)], fill=color, width=5)
    draw.line([(x1, y1 + radius), (x1, y2 - radius)], fill=color, width=5)
    draw.line([(x2, y1 + radius), (x2, y2 - radius)], fill=color, width=5)
    # Text
    draw.text((x1 + 45, y1 + 35), title, fill=color, font=font_large)
    y_offset = 105
    for line in lines:
        draw.text((x1 + 45, y1 + y_offset), line, fill=colors['text'] if y_offset < 155 else colors['text_gray'], font=font_small)
        y_offset += 50

def draw_agent(draw, x, y, icon, label, detail, color):
    draw.ellipse([x, y, x+104, y+104], outline=color, width=3, fill=colors['bg'])
    draw.text((x+22, y+18), icon, fill=color, font=font_icon)
    draw.text((x-20, y+115), label, fill=colors['text'], font=font_normal)
    draw.text((x-25, y+162), detail, fill=colors['text_gray'], font=font_small)

def draw_arrow(draw, x1, y1, x2, y2, color, width=3):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_size = 16
    draw.polygon([
        (x2, y2),
        (x2 - arrow_size * math.cos(angle - math.pi/6), y2 - arrow_size * math.sin(angle - math.pi/6)),
        (x2 - arrow_size * math.cos(angle + math.pi/6), y2 - arrow_size * math.sin(angle + math.pi/6))
    ], fill=color)

# Title
draw.text((120, 72), "AI Troubleshooter Architecture", fill=colors['cyan'], font=font_title)

# Observability banner
draw.text((120, 168), "☁️ Observability: LangSmith Cloud", fill=colors['cyan'], font=font_normal)

# ============================================================================
# ROW 1: Data Sources and User Input
# ============================================================================
draw_box(draw, (120, 264, 660, 520), colors['green'], "AWS OpenSearch", 
         ["Logs Database"])
draw_box(draw, (730, 264, 1170, 520), colors['green'], "EventRouter",
         ["K8s Events", "openshift-logging"])
draw_box(draw, (1240, 264, 1680, 520), colors['purple'], "User Input",
         ["Question/Query"])
draw_box(draw, (1710, 264, 2440, 620), colors['purple'], "Model Selection",
         ["6 Models Available:", "Llama 3.2 3B", "Groq 70B", "GPT-4o", "GPT-4o Mini"])

# ============================================================================
# ROW 2: Preprocessing
# ============================================================================
draw_box(draw, (120, 600, 672, 860), colors['purple'], "Embedder",
         ["Granite 125M", "LlamaStack"])
draw_box(draw, (768, 600, 1320, 860), colors['green'], "FAISS",
         ["Vector Storage", "In-memory"])
draw_box(draw, (1416, 600, 1920, 860), colors['orange'], "BM25",
         ["Keyword Search"])

# Arrows from Row 1 to Preprocessing
draw_arrow(draw, 390, 520, 390, 600, colors['green'], 4)  # AWS to Embedder
draw.text((410, 550), "~999 logs", fill=colors['text'], font=font_label)

draw_arrow(draw, 950, 520, 480, 600, colors['green'], 4)  # EventRouter to Embedder
draw.text((680, 540), "K8s events", fill=colors['text'], font=font_label)

draw_arrow(draw, 1460, 520, 480, 600, colors['purple'], 4)  # User Input to Embedder

# Arrows to BM25
draw_arrow(draw, 390, 520, 1668, 600, colors['green'], 4)  # AWS OpenSearch to BM25
draw_arrow(draw, 950, 520, 1668, 600, colors['green'], 4)  # EventRouter to BM25
draw_arrow(draw, 1460, 520, 1668, 600, colors['purple'], 4)  # User Input to BM25

# Arrow Embedder to FAISS
draw_arrow(draw, 672, 730, 768, 730, colors['purple'], 4)
draw.text((680, 705), "768-dim vectors", fill=colors['text'], font=font_label)

# ============================================================================
# MAIN RAG WORKFLOW BOX
# ============================================================================
rag_x1, rag_y1, rag_x2, rag_y2 = 120, 960, 3240, 2040
radius = 32
# Background
draw.rectangle([rag_x1 + radius, rag_y1, rag_x2 - radius, rag_y2], fill=colors['bg'])
draw.rectangle([rag_x1, rag_y1 + radius, rag_x2, rag_y2 - radius], fill=colors['bg'])
draw.pieslice([rag_x1, rag_y1, rag_x1 + radius*2, rag_y1 + radius*2], 180, 270, fill=colors['bg'])
draw.pieslice([rag_x2 - radius*2, rag_y1, rag_x2, rag_y1 + radius*2], 270, 360, fill=colors['bg'])
draw.pieslice([rag_x1, rag_y2 - radius*2, rag_x1 + radius*2, rag_y2], 90, 180, fill=colors['bg'])
draw.pieslice([rag_x2 - radius*2, rag_y2 - radius*2, rag_x2, rag_y2], 0, 90, fill=colors['bg'])
# Border
draw.arc([rag_x1, rag_y1, rag_x1 + radius*2, rag_y1 + radius*2], 180, 270, fill=colors['blue'], width=4)
draw.arc([rag_x2 - radius*2, rag_y1, rag_x2, rag_y1 + radius*2], 270, 360, fill=colors['blue'], width=4)
draw.arc([rag_x1, rag_y2 - radius*2, rag_x1 + radius*2, rag_y2], 90, 180, fill=colors['blue'], width=4)
draw.arc([rag_x2 - radius*2, rag_y2 - radius*2, rag_x2, rag_y2], 0, 90, fill=colors['blue'], width=4)
draw.line([(rag_x1 + radius, rag_y1), (rag_x2 - radius, rag_y1)], fill=colors['blue'], width=4)
draw.line([(rag_x1 + radius, rag_y2), (rag_x2 - radius, rag_y2)], fill=colors['blue'], width=4)
draw.line([(rag_x1, rag_y1 + radius), (rag_x1, rag_y2 - radius)], fill=colors['blue'], width=4)
draw.line([(rag_x2, rag_y1 + radius), (rag_x2, rag_y2 - radius)], fill=colors['blue'], width=4)

# RRF Fusion box (drawn AFTER the RAG workflow box so it appears on top)
draw_box(draw, (168, 1000, 720, 1160), colors['cyan'], "RRF Fusion",
         ["Combine Rankings"])

# Arrows from FAISS and BM25 to RRF Fusion
draw_arrow(draw, 1044, 860, 444, 1000, colors['green'], 4)  # FAISS to RRF
draw.text((700, 910), "Top 10 each", fill=colors['text'], font=font_label)

draw_arrow(draw, 1668, 860, 444, 1000, colors['orange'], 4)  # BM25 to RRF
draw.text((1000, 910), "Top 10 each", fill=colors['text'], font=font_label)

# Arrow from RRF Fusion to RETRIEVE
draw_arrow(draw, 444, 1160, 432, 1152, colors['cyan'], 4)
draw.text((350, 1120), "20 candidates", fill=colors['text'], font=font_label)

# Agents Row 1
draw_agent(draw, 348, 1152, "🔍", "RETRIEVE", "BM25+FAISS", colors['cyan'])
draw_agent(draw, 924, 1152, "⚡", "RERANK", "BGE v2-m3", colors['orange'])
draw_agent(draw, 1500, 1152, "✓", "GRADE", "Filter", colors['green'])
draw_agent(draw, 2076, 1152, "✨", "GENERATE", "Selected Model", colors['purple'])

# 5-Agent RAG Workflow title (bottom right)
draw.text((2300, 1920), "5-Agent RAG Workflow", fill=colors['cyan'], font=font_title)

# Arrows between agents (linear flow)
draw_arrow(draw, 504, 1236, 924, 1236, colors['text_gray'], 4)
draw.text((650, 1210), "20 docs", fill=colors['text'], font=font_label)

draw_arrow(draw, 1080, 1236, 1500, 1236, colors['text_gray'], 4)
draw.text((1220, 1210), "Top 10 ranked", fill=colors['text'], font=font_label)

draw_arrow(draw, 1656, 1236, 2076, 1236, colors['text_gray'], 4)
draw.text((1800, 1210), "✓ Good", fill=colors['text'], font=font_label)

# TRANSFORM Agent (below)
draw_agent(draw, 1212, 1584, "🔄", "TRANSFORM", "Query Rewrite", colors['red'])

# Arrow from GENERATE to TRANSFORM (retry path)
draw_arrow(draw, 2160, 1308, 1344, 1584, colors['red'], 4)
draw.text((1680, 1420), "✗ Retry", fill=colors['text'], font=font_label)

# Arrow from GRADE to TRANSFORM (poor results path)
draw_arrow(draw, 1584, 1308, 1296, 1584, colors['red'], 4)
draw.text((1380, 1420), "✗ Poor", fill=colors['text'], font=font_label)

# Loop back arrow (smooth curved path)
loop_points = [
    (1212, 1668),
    (1104, 1728),
    (960, 1788),
    (792, 1848),
    (600, 1896),
    (432, 1920),
    (288, 1920),
    (192, 1896),
    (156, 1848),
    (144, 1776),
    (156, 1680),
    (180, 1584),
    (216, 1488),
    (264, 1392),
    (312, 1320),
    (348, 1272),
    (372, 1248)
]
for i in range(len(loop_points) - 1):
    draw.line([loop_points[i], loop_points[i+1]], fill=colors['cyan'], width=5)

# Arrow head at RETRIEVE
draw.polygon([(372, 1248), (355, 1265), (379, 1267)], fill=colors['cyan'])

# Loop label
draw.text((156, 1728), "Loop back", fill=colors['cyan'], font=font_small)
draw.text((156, 1764), "(max 3x)", fill=colors['cyan'], font=font_small)

# Info text
draw.text((168, 1944), "Self-correcting system with iterative refinement", fill=colors['text_gray'], font=font_small)

# ============================================================================
# EXTERNAL SERVICES (Right side)
# ============================================================================
draw_box(draw, (3360, 960, 3960, 1250), colors['yellow'], "LlamaStack",
         ["Llama 3.2 3B", "Granite 125M embeddings"])
draw_box(draw, (3360, 1296, 3960, 1586), colors['yellow'], "BGE Reranker",
         ["vLLM Service", "BAAI/bge-reranker-v2-m3"])
draw_box(draw, (4080, 960, 4608, 1196), colors['cyan'], "☁️ Groq API",
         ["Llama 3.3 70B"])
draw_box(draw, (4080, 1248, 4608, 1484), colors['cyan'], "☁️ OpenAI",
         ["GPT-4o / Mini"])

# Connections to external services
draw_arrow(draw, 3360, 1092, 672, 720, colors['yellow'], 4)  # LlamaStack to Embedder
draw_arrow(draw, 3360, 1152, 2232, 1236, colors['yellow'], 4)  # LlamaStack to Generate
draw_arrow(draw, 3360, 1428, 1080, 1236, colors['yellow'], 4)  # BGE to Rerank
draw_arrow(draw, 4080, 1068, 2232, 1200, colors['cyan'], 3)     # Groq to Generate
draw_arrow(draw, 4080, 1356, 2232, 1272, colors['cyan'], 3)     # OpenAI to Generate

# Model Selection to Generate
draw_arrow(draw, 2075, 620, 2160, 1152, colors['purple'], 3)

# ============================================================================
# OUTPUT SECTION
# ============================================================================
draw.text((120, 2160), "Output Paths:", fill=colors['red'], font=font_large)

draw_box(draw, (120, 2256, 912, 2520), colors['red'], "Markdown",
         ["Human-readable", "➜ Streamlit UI"])
draw_box(draw, (1008, 2256, 1800, 2520), colors['red'], "JSON",
         ["Machine-readable", "➜ EDA Webhook"])

# Simple arrows from GENERATE to outputs
draw_arrow(draw, 2160, 1308, 516, 2256, colors['purple'], 4)
draw.text((1200, 1720), "✓ Done", fill=colors['text'], font=font_label)

draw_arrow(draw, 2160, 1308, 1404, 2256, colors['purple'], 4)
draw.text((1750, 1720), "✓ Done", fill=colors['text'], font=font_label)

# ============================================================================
# INFRASTRUCTURE PLATFORM
# ============================================================================
draw.text((1920, 2160), "Infrastructure Platform:", fill=colors['red'], font=font_large)
draw_box(draw, (1920, 2256, 3960, 2520), colors['red'], "ROSA/RHOAI",
         ["Python 3.11", "LlamaStack", "OpenShift MCP Server"])

# Save
img.save('/mnt/user-data/outputs/rag_architecture_simplified.png')
print("✅ Simplified diagram created - no decision logic, FAISS → RETRIEVE only!")
