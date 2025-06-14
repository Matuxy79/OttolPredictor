"""
Embedded chart widgets for inline display - no more popup windows!
"""
import matplotlib
matplotlib.use('Qt5Agg')  # Force Qt backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class EmbeddedChartWidget(QWidget):
    """Widget that safely embeds matplotlib figures"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.current_canvas = None
        
    def display_figure(self, fig: Figure):
        """Display a matplotlib figure, replacing any existing one"""
        try:
            # Clear existing canvas
            self.clear_canvas()
            
            # Create new canvas
            self.current_canvas = FigureCanvas(fig)
            self.layout.addWidget(self.current_canvas)
            
            # Force redraw
            self.current_canvas.draw()
            
            logger.debug("Successfully displayed embedded chart")
            
        except Exception as e:
            logger.error(f"Error displaying figure: {e}")
            self.display_error(f"Chart Error: {e}")
    
    def display_error(self, error_message: str):
        """Display an error message instead of a chart"""
        self.clear_canvas()
        
        error_label = QLabel(error_message)
        error_label.setStyleSheet("""
            QLabel {
                color: #d32f2f;
                font-size: 14px;
                padding: 20px;
                background-color: #ffebee;
                border: 1px solid #ffcdd2;
                border-radius: 4px;
            }
        """)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setWordWrap(True)
        self.layout.addWidget(error_label)
    
    def display_no_data(self, message: str = "No data available"):
        """Display a no-data message"""
        self.clear_canvas()
        
        no_data_label = QLabel(message)
        no_data_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                padding: 20px;
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        no_data_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(no_data_label)
    
    def clear_canvas(self):
        """Remove any existing canvas or widget"""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        self.current_canvas = None

def render_text_figure(message: str, title: str = "") -> Figure:
    """Create a figure that displays only text - perfect for error states"""
    fig = Figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    
    # Display the message
    ax.text(0.5, 0.5, message, 
            horizontalalignment='center', 
            verticalalignment='center',
            transform=ax.transAxes, 
            fontsize=14,
            wrap=True)
    
    # Set title if provided
    if title:
        ax.set_title(title, fontsize=16, pad=20)
    
    # Hide axes
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    fig.tight_layout()
    return fig