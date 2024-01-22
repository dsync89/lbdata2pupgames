import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QItemDelegate, QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QTableView, QComboBox, QStyledItemDelegate, QLabel, QFrame, QHBoxLayout, QLineEdit, QProgressBar, QHeaderView, QRadioButton, QDialog, QGridLayout, QStyleOptionViewItem, QCheckBox, QGroupBox, QSizePolicy
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush

from PyQt5.QtGui import QPixmap
from fuzzywuzzy import fuzz

import shutil 
import re

import json
import xmltodict

import debugpy

debugpy.listen(('localhost', 5678))

# DIR1 = "r:\\ROMS-1G1R\\pinball\\Visual Pinball\\test"
# DIR2 = "c:\\PinUPSystem\\POPMedia\\Visual Pinball X\\Audio"
OUT_DIR = "tests\\out"

LB_PLATFORM_DATA_PATH = os.path.join("Data", "Platforms")

class ComboBoxDelegate(QItemDelegate):
    def __init__(self, parent=None, options=None, DIR2=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.options = options or []
        self.DIR2 = DIR2  # Store DIR2 as an instance variable

    def set_DIR2(self, DIR2):
        self.DIR2 = DIR2        

    def createEditor(self, parent, option, index):
        button = QPushButton("Select Image", parent)
        button.clicked.connect(lambda _, index=index: self.open_popup_dialog(index))

        return button

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, editor, model, index):
        pass

    def open_popup_dialog(self, index):
        pass
        # options = self.options.get(index.row(), [])
        # dialog = ImagePopupDialog(options, self.DIR2, self.parent())

        # if dialog.exec_() == QDialog.Accepted:
        #     selected_option = dialog.selected_option
        #     if selected_option:
        #         index.model().setData(index, selected_option, role=Qt.EditRole)
        #         index.model().layoutChanged.emit()

    # def paint(self, painter, option, index):
    #     super().paint(painter, option, index)

    #     # Check if the text in the third column contains 'abc'
    #     if index.column() == 2 and '24' in index.data(Qt.DisplayRole):
    #         # Highlight the item by drawing a colored background
    #         option = QStyleOptionViewItem(option)
    #         option.palette.setColor(option.palette.Highlight, QColor(255, 255, 0))  # Yellow color
    #         option.palette.setColor(option.palette.HighlightedText, QColor(0, 0, 0))  # Black color
    #         self.drawBackground(painter, option, index)                

    def data(self, index, role):
        if role == Qt.BackgroundRole and index.column() == 2 and '24' in index.data(Qt.DisplayRole):
            return QBrush(QColor(255, 255, 0))  # Yellow color
        return super().data(index, role)

class ConvertThread(QThread):
    progressUpdated = pyqtSignal(int)
    fileProcessed = pyqtSignal(str)
    resultReady = pyqtSignal(object)


    def __init__(self, parent=None):
        super(ConvertThread, self).__init__(parent)
        self.lb_platform_xml_file_paths = ""
        self.out_dir = ""

    def setDirectories(self, dir_1_path, dir_2_path):
        self.lb_platform_xml_file_paths = dir_1_path
        self.out_dir = dir_2_path

    def run(self):
        debugpy.breakpoint()
        fuzzy_match_results = self.perform_convert(self.lb_platform_xml_file_paths, self.out_dir)
        self.progressUpdated.emit(100)  # Signal completion
        self.resultReady.emit(fuzzy_match_results)

    # convert launchbox platform.xml file to .pupgames
    def perform_convert(self, lb_platform_xml_file_paths, out_dir): 
        results = ''
        processed_files = 0
        total_files = len(lb_platform_xml_file_paths)
        for xml_file_path in lb_platform_xml_file_paths:
            
            with open(xml_file_path, 'r', encoding='utf-8') as file:
                xml_content = file.read()

            json_result = self.convert_xml_to_json(xml_content)     
            
            # Process the entire dictionary
            processed_dict = self.replace_null_with_empty(json_result)   

            # Save JSON to a file
            out_json_filename = os.path.join(out_dir, f"{os.path.splitext(os.path.basename(xml_file_path))[0]}.pupgames")
            with open(f'{out_json_filename}', 'w') as outfile:
                json.dump(processed_dict, outfile, indent=2)

            print(f"JSON saved to {out_json_filename}")                                 

            processed_files += 1
            progress_percentage = int(processed_files / total_files * 100)
            self.progressUpdated.emit(progress_percentage)
            self.fileProcessed.emit(os.path.basename(xml_file_path))

        return results
    
    def convert_xml_to_json(self, xml_string):
        xml_dict = xmltodict.parse(xml_string, force_list=False)
        games = xml_dict["LaunchBox"]["Game"]

        # force convert a dict, {} to list [], for xml that only has 1 game
        if isinstance(games, dict):
            games_ = []
            games_.append(games)
            games = games_
        
        game_export = []
        for i, game in enumerate(games, start=0):
            game_export.append(self.map_fields(game, i))

        return {"GameExport": game_export}
    
    def map_fields(self, game, index):
        # Extracting the filename using regex
        application_path = game.get("ApplicationPath")
        
        if application_path is not None:
            match = re.search(r'\\([^\\]+)$', application_path)
            gameFileName = match.group(1) if match else ""
        else:
            gameFileName = ""

        # Helper function to get the value or an empty string if it's None
        def get_value(key):
            return game.get(key, "")
        
        def get_media_search_value(key):
            result = game.get(key, "").replace(":", "_").replace("/", "_").replace("'", "_")
            return f'{result}*'
        
        return {
            "GameID": str(index + 1),
            "GameName": get_value("Title"),
            "GameFileName": gameFileName,
            "GameDisplay": get_value("Title"),
            "UseEmuDefaults": "",
            "Visible": "1",
            "Notes": get_value("Notes"),
            "DateAdded": get_value("DateAdded"),
            "GameYear": get_value("ReleaseDate"),
            "ROM": "",
            "Manufact": get_value("Publisher"),
            "NumPlayers": get_value("MaxPlayers"),
            "ResolutionX": "",
            "ResolutionY": "",
            "OutputScreen": "",
            "ThemeColor": "",
            "GameType": "",
            "TAGS": "",
            "Category": get_value("Genre"),
            "Author": "",
            "LaunchCustomVar": "",
            "GKeepDisplays": "",
            "GameTheme": "General",
            "GameRating": "",
            "Special": "",
            "sysVolume": "",
            "DOFStuff": "",
            "MediaSearch": get_media_search_value("Title"),
            "AudioChannels": "",
            "CUSTOM2": get_value("Region"),
            "CUSTOM3": "",
            "GAMEVER": get_value("Version"),
            "ALTEXE": "",
            "IPDBNum": "",
            "DateUpdated": "",
            "DateFileUpdated": "",
            "AutoRecFlag": "0",
            "AltRunMode": "",
            "WebLinkURL": get_value("WikipediaURL"),
            "DesignedBy": "",
            "CUSTOM4": "",
            "CUSTOM5": "",
            "WEBGameID": "",
            "ROMALT": "",
            "ISMOD": "0",
            "FLAG1": "0",
            "FLAG2": "0",
            "FLAG3": "0",
            "gLog": "",
            "RatingWeb": get_value("CommunityStarRating"),
            "WebLink2URL": "",
            "TourneyID": "",
            "EmuDisplay": get_value("Platform"),
            "DirGamesShare": "",
            "DirMedia": "",
            "DirMediaShare": ""
        }

    def replace_null_with_empty(self, obj):
        if isinstance(obj, list):
            return [self.replace_null_with_empty(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self.replace_null_with_empty(value) for key, value in obj.items()}
        else:
            return "" if obj is None else obj

class Lb2PupGames(QMainWindow):
    progressUpdated = pyqtSignal(int)
    fileProcessed = pyqtSignal(str)
    resultReady = pyqtSignal(object)

    def update_status_label(self, filename):
        if len(filename) > 50:
            filename = filename[:47] + "..."  # Display only the first 47 characters and add ellipsis
        self.status_label.setText(f"Processing: {filename}")      

    def __init__(self):
        super(Lb2PupGames, self).__init__()

        self.setWindowTitle("Launchbox2PupGames Converter")
        self.setGeometry(100, 100, 1280, 720)

        self.dir_1_path = ""
        self.dir_2_path = ""
        self.DIR1 = ""
        self.DIR2 = ""     

        self.settings = {
            "lb_folder_dir": "C:\\Programs\\Launchbox",
            "output_dir": "c:\\Users\\Gary\\Documents\\Github-dsync89\\lbdata2pupgames\\out\\_pupgames",
            "selected_platform_xml": []
        }

        if not os.path.exists(self.settings["output_dir"]):
            os.makedirs(self.settings["output_dir"])
                
        self.setup_ui()
        self.init_ui_values()

    def init_ui_values(self):
        self.lb_folder_chosen_textfield.setText(self.settings["lb_folder_dir"])
        self.out_folder_chosen_textfield.setText(self.settings["output_dir"])

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()

        # Left frame
        left_frame = QFrame(self)
        left_frame.setFixedWidth(350)  # Set the minimum width
        left_layout = QVBoxLayout(left_frame)
        left_layout.setAlignment(Qt.AlignTop)
    
        # Pair 1: Dir 1 Label and Button
        pair_1_layout = QHBoxLayout()
        lb_folder_label = QLabel("Launchbox Folder:", left_frame)
        lb_folder_chosen_textfield = QLineEdit("", left_frame)  # New text field to display chosen dir path
        lb_folder_chosen_textfield.setReadOnly(False)  # allow user to paste its path
        lb_folder_select_button = QPushButton("...", left_frame)
        lb_folder_select_button.clicked.connect(self.browse_lb_folder)
        lb_folder_select_button.setFixedSize(20, lb_folder_select_button.sizeHint().height())
        pair_1_layout.addWidget(lb_folder_label)
        pair_1_layout.addWidget(lb_folder_chosen_textfield)  # Add the new label
        pair_1_layout.addWidget(lb_folder_select_button)
        left_layout.addLayout(pair_1_layout)

        # Pair 2: Dir 2 Label and Button
        pair_2_layout = QHBoxLayout()
        out_folder_label = QLabel("Output Dir (.pupgames):", left_frame)
        out_folder_chosen_textfield = QLineEdit("", left_frame)  # New text field to display chosen dir path
        out_folder_chosen_textfield.setReadOnly(False)  # allow user to paste its path
        out_folder_select_button = QPushButton("...", left_frame)
        out_folder_select_button.clicked.connect(self.browse_output_folder)
        out_folder_select_button.setFixedSize(20, out_folder_select_button.sizeHint().height())
        pair_2_layout.addWidget(out_folder_label)
        pair_2_layout.addWidget(out_folder_chosen_textfield)
        pair_2_layout.addWidget(out_folder_select_button)  # Add the new label
        left_layout.addLayout(pair_2_layout)

        # Button to start listing all xmls
        start_scan_lb_platforms_xml_btn = QPushButton("Scan Platforms XML", left_frame)
        start_scan_lb_platforms_xml_btn.clicked.connect(self.onclick_btn_update_lb_data_platform_xml)
        left_layout.addWidget(start_scan_lb_platforms_xml_btn)

        # Button to start fuzzy match
        start_match_button = QPushButton("Start Match", left_frame)
        start_match_button.clicked.connect(self.start_fuzzy_match)
        left_layout.addWidget(start_match_button)

        # Status label
        self.status_label = QLabel("Processing...", left_frame)
        left_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar(left_frame)
        left_layout.addWidget(self.progress_bar)  

        # Set size policy for progress bar to Expanding
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)        

        # Statistics label
        # self.statistics_label = QLabel("Statistics: 0 empty cells in Column 3", left_frame)
        # left_layout.addWidget(self.statistics_label)    

        # Add vertical spacer between the QGroupBox widgets
        left_layout.addSpacing(10)




        layout.addWidget(left_frame)
        

        # add to self so that other class can refer
        self.lb_folder_chosen_textfield = lb_folder_chosen_textfield
        self.out_folder_chosen_textfield = out_folder_chosen_textfield

        # --------------


        # Right frame
        right_frame = QFrame(self)
        right_layout = QVBoxLayout(right_frame)

        self.table_view = QTableView(self)
        right_layout.addWidget(self.table_view)

        # "Select All" checkbox
        select_all_checkbox = QCheckBox("Select All", left_frame)
        select_all_checkbox.stateChanged.connect(self.select_all_checkboxes)        
        right_layout.addWidget(select_all_checkbox)

        start_convert_btn = QPushButton("Convert", right_frame)
        start_convert_btn.clicked.connect(self.onclickbtn_start_convert)
        start_convert_btn.setFixedSize(200, 50)  # Set the width and height as needed        
        right_layout.addWidget(start_convert_btn)

        layout.addWidget(right_frame)

        central_widget.setLayout(layout)

        # Initialize the table view with an empty model
        self.model = QStandardItemModel(self)
        self.model.setColumnCount(2)
        self.model.setHorizontalHeaderLabels(["XML Files", "Select"])
        self.table_view.setModel(self.model)

        self.options_list = {}

        # must initialize at least one
        self.options_list[0] = "zzz"

        # Set custom delegate for the third column
        combo_box_delegate = ComboBoxDelegate(self.table_view, options=self.options_list, DIR2=self.DIR2)
        self.table_view.setItemDelegateForColumn(2, combo_box_delegate)

        # Connect the stateChanged signal of checkboxes to the slot update_selected_platform_xml
        self.table_view.model().itemChanged.connect(self.update_selected_platform_xml)


        # Set column widths
        for col in range(self.model.columnCount()):
            self.table_view.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

        # Set the last section to stretch, ensuring it fills the remaining width
        self.table_view.horizontalHeader().setStretchLastSection(True)

        # Set column widths
        self.table_view.resizeColumnsToContents()
        # self.table_view.setColumnWidth(0, 1000)
        # self.table_view.setColumnWidth(1, 500)


    def select_all_checkboxes(self, state):
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 1)  # Assuming checkbox is in the second column

            if item is not None:
                item.setCheckState(state)    

    def show_directory_error_dialog(self):
        error_dialog = QDialog(self)
        error_dialog.setWindowTitle("Directory Error")
        error_dialog.setGeometry(300, 300, 400, 100)

        layout = QVBoxLayout()

        error_label = QLabel("One or both of the selected directories are invalid or do not exist.")
        layout.addWidget(error_label)

        ok_button = QPushButton("OK", error_dialog)
        ok_button.clicked.connect(error_dialog.accept)
        layout.addWidget(ok_button)

        error_dialog.setLayout(layout)
        error_dialog.exec_()        

    def start_fuzzy_match(self):
        # check if dir is valid, it not display error as popup dialog
        dir_1_path = self.leftframe_dir_1_chosen_textfield.text()
        dir_2_path = self.leftframe_dir_2_chosen_textfield.text()

        if not os.path.isdir(dir_1_path) or not os.path.isdir(dir_2_path):
            self.show_directory_error_dialog()
            return        
        
        self.progress_bar.setValue(0)  # Reset progress bar
        self.status_label.setText("Processing...")

        self.convert_thread.setDirectories(dir_1_path, dir_2_path)
        self.convert_thread.start()        

        self.DIR1 = dir_1_path
        self.DIR2 = dir_2_path

        # update comboboxdelgate
        combo_box_delegate = self.table_view.itemDelegateForColumn(2)
        if combo_box_delegate:
            combo_box_delegate.set_DIR2(self.DIR2)

    def update_status_label(self, filename):
        if len(filename) > 50:
            filename = filename[:47] + "..."  # Display only the first 47 characters and add ellipsis
        self.status_label.setText(f"Processing: {filename}")   

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)     

    def browse_lb_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Launchbox program folder")
        if directory:
            self.settings["lb_folder_dir"] = directory
            self.lb_folder_chosen_textfield.setText(directory)  # Update the label text

    def browse_output_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select output dir for .pupgames")
        if directory:
            self.settings["output_dir"] = directory
            self.out_folder_chosen_textfield.setText(directory)  # Update the label text

    def list_xml_files(self, folder_path, file_extension):
        xml_files = []

        # Check if the folder exists
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # Iterate through files in the folder
            for filename in os.listdir(folder_path):
                # Check if the file has a .xml extension
                if filename.endswith(file_extension):
                    xml_files.append(filename)

        return xml_files

    def onclick_btn_update_lb_data_platform_xml(self):
        lb_platforms_data_xml_dir = os.path.join(self.settings["lb_folder_dir"], "Data", "Platforms")
        xml_files = self.list_xml_files(lb_platforms_data_xml_dir, ".xml")

        # Update the right QTableView with the list of XML files
        self.update_right_table_view(xml_files)        

    def update_right_table_view(self, xml_files):
        # Clear the existing data in the model
        self.model.clear()

        # Set the column count and header labels for the right QTableView
        self.model.setColumnCount(2)
        self.model.setHorizontalHeaderLabels(["XML Files", "Select"])

        # Iterate through the XML files and add each file with a checkbox to the model
        for xml_file in xml_files:
            # Create an item for the XML file name
            xml_item = QStandardItem(xml_file)

            # Create a checkbox item for the second column
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            checkbox_item.setCheckState(Qt.Unchecked)

            # Add the items to the model
            self.model.appendRow([xml_item, checkbox_item])

        # Set column widths based on contents
        self.table_view.resizeColumnsToContents()  
                 
        self.table_view.setColumnWidth(1, 100)

        # Update the right QTableView with the modified model
        self.table_view.setModel(self.model)

    def update_selected_platform_xml(self, item):
        # Check if the item is a checkbox in the second column
        if item.column() == 1:
            # Get the XML filename from the corresponding row in the first column
            xml_filename_item = self.model.item(item.row(), 0)
            xml_filename = xml_filename_item.text()

            # Check if the checkbox is checked or unchecked
            if item.checkState() == Qt.Checked:
                # Add the XML filename to the selected_platform_xml list if checked
                if xml_filename not in self.settings["selected_platform_xml"]:
                    self.settings["selected_platform_xml"].append(xml_filename)
            else:
                # Remove the XML filename from the selected_platform_xml list if unchecked
                self.settings["selected_platform_xml"].remove(xml_filename)


    def update_table_view_with_fuzzy_match(self, fuzzy_match_results):
        pass
        # self.model.clear()
        # self.model.setColumnCount(4)
        # self.model.setHorizontalHeaderLabels([".ahk Filename", "Fuzzy Matched Image", "Detected Images", "Chosen Image"])

        # empty_cells_count = 0  # Counter for empty cells in column 3        
        # total_rows_column_1 = 0  # Counter for total rows in column 1

        # for index, result in enumerate(fuzzy_match_results):
        #     item_1 = QStandardItem(result[0])
        #     item_2 = QStandardItem(result[1][2])
        #     item_3 = QStandardItem(result[1][2])

        #     total_rows_column_1 += 1  # Increment count for total rows in column 1

        #     detected_images = []

        #     for file, ratio in result[2]:
        #         # if ratio > 40:
        #         detected_images.append((file, ratio))

        #     detected_images_sorted_data = sorted(detected_images, key=lambda x: x[1], reverse=True)
        #     self.options_list[index] = detected_images_sorted_data

        #     # Add the chosen image as the 4th column
        #     chosen_image_filename = result[1][2]  # Assuming result[1] is the chosen image filename
        #     chosen_image_item = QStandardItem()
        #     chosen_image_path = os.path.join(self.DIR2, chosen_image_filename)
        #     pixmap = QPixmap(chosen_image_path).scaledToWidth(100)
        #     chosen_image_item.setData(pixmap, Qt.DecorationRole)    

        #     # colorize
        #     try:
        #         if detected_images_sorted_data[0][1] >= 100:
        #             item_3.setBackground(QBrush(QColor(0, 255, 0))) 
        #         elif detected_images_sorted_data[0][1] >= 80:
        #             item_3.setBackground(QBrush(QColor(0, 200, 0))) 
        #         elif detected_images_sorted_data[0][1] >= 65:
        #             item_3.setBackground(QBrush(QColor(255, 255, 0))) # yellow
        #         elif detected_images_sorted_data[0][1] < 65:
        #             item_3 = QStandardItem("")
        #             empty_cells_count += 1  # Increment count for empty cells

        #     except Exception as e:
        #         print(f"An error occurred: {e}") 
        #         item_3 = QStandardItem("")        
        #         empty_cells_count += 1  # Increment count for empty cells        

        #     self.model.appendRow([item_1, item_2, item_3, chosen_image_item])

        # # Update the statistics label
        # # total_matched_cells = total_rows_column_1 - empty_cells_count
        # # percentage_matched_cells = int ( ( total_matched_cells / total_rows_column_1 ) * 100 ) 
        # # self.statistics_label.setText(f"Statistics: {total_matched_cells} / {total_rows_column_1} [{percentage_matched_cells}%] matched cells in Column 3")

        # self.table_view.setModel(self.model)

    def onclickbtn_start_convert(self):
        lb_platform_xml_filepaths = []
        out_pupgames_dir = self.settings["output_dir"]

        for platform_xml in self.settings["selected_platform_xml"]:
            src_filepath = os.path.join(self.settings["lb_folder_dir"], LB_PLATFORM_DATA_PATH, platform_xml)
            lb_platform_xml_filepaths.append(src_filepath)

        self.convert_thread = ConvertThread()
        self.convert_thread.resultReady.connect(self.update_table_view_with_fuzzy_match)
        self.convert_thread.progressUpdated.connect(self.update_progress_bar)
        self.convert_thread.fileProcessed.connect(self.update_status_label)

        self.convert_thread.setDirectories(lb_platform_xml_filepaths, out_pupgames_dir)
        self.convert_thread.start()                  


        # column_1_values = self.get_column_values(0)
        # column_2_values = self.get_column_values(1)
        # column_3_values = self.get_column_values(2)

        # for index, filename in enumerate(column_3_values):
        #     if len(filename.strip()) == 0:
        #         continue

        #     if '|' in filename:
        #         parts = filename.split('|')
        #         filename = parts[1].strip()

        #     ahk_filename, ahk_file_extension = os.path.splitext(column_1_values[index])
        #     img_filename, img_file_extension = os.path.splitext(filename)

        #     src_file = os.path.join(self.DIR2, filename)
        #     dest_file = os.path.join(OUT_DIR, f"{ahk_filename}{img_file_extension}")
        #     print(f"Copying [ {src_file} ] => [ {dest_file} ]")
        #     shutil.copy2(src_file, dest_file)

    def get_column_values(self, col_idx):
        column_values = []

        for row in range(self.model.rowCount()):
            item = self.model.item(row, col_idx)

            if item is not None:
                column_values.append(item.text())

        print("Column values:", column_values)
        return column_values

def main():
    app = QApplication([])
    window = Lb2PupGames()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()