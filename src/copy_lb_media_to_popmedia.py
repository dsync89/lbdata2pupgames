# A window app that copy launchbox media to POPMedia
import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QItemDelegate, QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QTableView, QComboBox, QStyledItemDelegate, QLabel, QFrame, QHBoxLayout, QLineEdit, QProgressBar, QHeaderView, QRadioButton, QDialog, QGridLayout, QStyleOptionViewItem, QCheckBox, QGroupBox, QSizePolicy, QButtonGroup, QLayout
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush

from PyQt5.QtGui import QPixmap
from fuzzywuzzy import fuzz

import shutil 
import re

import json
import xmltodict

import subprocess

import debugpy

debugpy.listen(('localhost', 5678))

# DIR1 = "r:\\ROMS-1G1R\\pinball\\Visual Pinball\\test"
# DIR2 = "c:\\PinUPSystem\\POPMedia\\Visual Pinball X\\Audio"
OUT_DIR = "tests\\out"

LB_PLATFORM_DATA_PATH = os.path.join("Data", "Platforms")
LB_IMAGES_DATA_PATH = os.path.join("Images")
LB_VIDEOS_DATA_PATH = os.path.join("Videos")

# for dropdown menu mapping
POPMEDIA_MEDIA_FOLDERS = [ "Topper", 
                          "DMD", 
                          "BackGlass", 
                          "PlayField", 
                          "Menu", 
                          "GameSelect", 
                          "Other1", 
                          "Other2", 
                          "GameInfo", 
                          "GameHelp", 
                          "Music"
                          ]

LAUNCHBOX_MEDIA_FOLDERS = [ "Advertisement Flyer - Front",       # 0
                           "Arcade - Controls Information",     # 1
                           "Arcade - Marquee",                  # 2
                           "Clear Logo",                        # 3
                           "Screenshot - Gameplay",             # 4
                           "Video Snaps",                       # 5
                           "Video Theme",                       # 6
                           "Video Marquee",                     # 7
                           ""                                  # 8
                           ]

MEDIA_DIR_MAPPING_DEFAULT_INDICES = [ 2,    # Topper
                                      3,    # DMD (4:1)
                                      5,    # Backglass
                                      6,    # Playfield
                                      8,    # Apron (FullDMD)
                                      4,    # Game Select/WheelBar
                                      8,    # Loading/Other1
                                      7,    # Other2
                                      0,    # GameInfo/Flyer
                                      1,    # GameHelp
                                      8,    # Music
                                    ]


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

    def setData(self, tuples, selected_copy_behaviour):
        self.tuples = tuples
        self.selected_copy_behaviour = selected_copy_behaviour

    def run(self):
        debugpy.breakpoint()
        fuzzy_match_results = self.perform_copy_link(self.tuples)
        self.progressUpdated.emit(100)  # Signal completion
        self.resultReady.emit(fuzzy_match_results)

    # tuples( ( platform_name, (src_folder_paths, dest_folder_paths) ) )

    def create_hard_link(self, source, destination):
        try:
            subprocess.run(['mklink', '/H', destination, source], check=True)
            print(f"Hard link created: {destination} -> {source}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating hard link: {e}")

    def create_hard_links_recursively(self, source_dir, destination_dir):
        for root, _, files in os.walk(source_dir):
            for file in files:
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, source_dir)
                destination_path = os.path.join(destination_dir, relative_path)

                self.create_hard_link(source_path, destination_path)

    def create_ntfs_junction(self, link, target):
        try:
            subprocess.run(['cmd', '/c', 'mklink', '/J', link, target], check=True)            
            print(f"NTFS junction created: {link} -> {target}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating NTFS junction: {e}")    

    def perform_copy_link(self, tuples): 
        results = ''
        processed_files = 0
        total_platforms = len(tuples)
        for platform_name, src_folder_paths, dest_folder_paths in tuples:
            print(f"Processing platform name: {platform_name}")    
            for i, src_folder_path in enumerate(src_folder_paths):
                dest_folder_path = dest_folder_paths[i]       

                if self.selected_copy_behaviour == 'copy':
                    try:
                        print(f"Copy {src_folder_path} ==> {dest_folder_path}")   
                        shutil.copytree(src_folder_path, dest_folder_path)  
                    except Exception as e:
                        print(f"Error copying tree: {e}")

                elif self.selected_copy_behaviour == 'hard_link': 
                    try:                      
                        print(f"Creating Hard Link {src_folder_path} <==> {dest_folder_path}") 
                        self.create_hard_links_recursively(src_folder_path, dest_folder_path)
                    except Exception as e:
                        print(f"Error creating hard link: {e}")

                elif self.selected_copy_behaviour == 'ntfs_junction': 
                    try:
                        # remove existing link
                        if os.path.exists(dest_folder_path):
                            print(f"Removing existing NTFS Junction: {dest_folder_path}")
                            os.remove(dest_folder_path)
                        os.makedirs(os.path.dirname(dest_folder_path), exist_ok=True) # remove the last element
                        print(f"Creating NTFS Junction {src_folder_path} <==> {dest_folder_path}") 
                        self.create_ntfs_junction(dest_folder_path, src_folder_path)
                    except Exception as e:
                        print(f"Error creating NTFS Junction Link: {e}")
            
                else:
                    print("Unknown copy behaviour! Why am I here!!?")

                print("")   


            processed_files += 1
            progress_percentage = int(processed_files / total_platforms * 100)
            self.progressUpdated.emit(progress_percentage)
            self.fileProcessed.emit(platform_name)

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

        self.setWindowTitle("Launchbox Media 2 POPMedia")
        self.setGeometry(100, 100, 1280, 720)

        self.dir_1_path = ""
        self.dir_2_path = ""
        self.DIR1 = ""
        self.DIR2 = ""     

        self.media_dir_mapping_dropdown_widgets = []  # List to store references to dropdown widgets

        self.settings = {
            "lb_folder_dir": "C:\\Programs\\Launchbox",
            "output_dir": "c:\\PinUPSystem\\POPMedia",
            "selected_platform_xml": [],
            "selected_copy_behaviour": 'ntfs_junction'
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
        left_frame.setFixedWidth(500)  # Set the minimum width
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
        out_folder_label = QLabel("POPMedia Folder:", left_frame)
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



        # ------------------------------------
        # Launchbox Settings Frame        
        # ------------------------------------
        # Left frame for Launchbox Settings
        launchbox_settings_groupbox = QGroupBox("Copy Behaviour", self)
        launchbox_settings_groupbox.setFixedWidth(300)  # Set the width of the Launchbox Settings groupbox
        launchbox_settings_layout = QVBoxLayout(launchbox_settings_groupbox)
        launchbox_settings_layout.setAlignment(Qt.AlignTop)

        # Create a button group
        self.button_group = QButtonGroup()

        # Radio button 1
        radio_button1 = QRadioButton("Create NTFS Junction Link", launchbox_settings_groupbox)
        launchbox_settings_layout.addWidget(radio_button1)
        self.button_group.addButton(radio_button1)
        radio_button1.setChecked(True)

        # Radio button 2
        radio_button2 = QRadioButton("Create Hard Link", launchbox_settings_groupbox)
        launchbox_settings_layout.addWidget(radio_button2)
        self.button_group.addButton(radio_button2)
        radio_button2.setDisabled(True) # TODO: not supported for now

        # Radio button 3
        radio_button3 = QRadioButton("Copy", launchbox_settings_groupbox)
        launchbox_settings_layout.addWidget(radio_button3)
        self.button_group.addButton(radio_button3)


        self.button_group.setExclusive(True)  # Set exclusive to make it behave like a radio button group

        # Connect the buttonClicked signal to a custom slot
        self.button_group.buttonClicked.connect(self.on_radio_button_clicked)


        # Add the Launchbox Settings groupbox to the left layout
        left_layout.addWidget(launchbox_settings_groupbox)

        # Add vertical spacer between the QGroupBox widgets
        left_layout.addSpacing(10)

        # Frame for Launchbox Dir Mappings
        dir_mappings_groupbox = QGroupBox("Launchbox Dir Mappings", self)
        dir_mappings_groupbox.setFixedWidth(300)  # Set the width of the Dir Mappings groupbox
        dir_mappings_layout = QGridLayout(dir_mappings_groupbox)
        dir_mappings_layout.setAlignment(Qt.AlignTop)

        # dir_mappings_label = QLabel("Left: POPMedia Folder, Right: Launchbox Media Folder", dir_mappings_groupbox)
        # dir_mappings_layout.addWidget(dir_mappings_label)

        self.dir_mappings_groupbox = dir_mappings_groupbox
        self.dir_mappings_layout = dir_mappings_layout
        self.create_media_mapping_dropdown_menu(POPMEDIA_MEDIA_FOLDERS, LAUNCHBOX_MEDIA_FOLDERS, MEDIA_DIR_MAPPING_DEFAULT_INDICES)

        # Dropdown 1 with Checkbox
        # dropdown_layout1 = QHBoxLayout()
        # dropdown_label1 = QLabel("Topper:", dir_mappings_groupbox)
        # dropdown1 = QComboBox(dir_mappings_groupbox)
        # dropdown1.addItems(["dir1", "dir2", "dir3"])
        # checkbox1 = QCheckBox("Option 1", dir_mappings_groupbox)
        # dropdown_layout1.addWidget(dropdown_label1)
        # dropdown_layout1.addWidget(dropdown1)
        # dropdown_layout1.addWidget(checkbox1)
        # dir_mappings_layout.addLayout(dropdown_layout1)

        # # Dropdown 2 with Checkbox
        # dropdown_layout2 = QHBoxLayout()
        # dropdown_label2 = QLabel("DMD:", dir_mappings_groupbox)
        # dropdown2 = QComboBox(dir_mappings_groupbox)
        # dropdown2.addItems(["dir1", "dir2", "dir3"])
        # checkbox2 = QCheckBox("Option 2", dir_mappings_groupbox)
        # dropdown_layout2.addWidget(dropdown_label2)
        # dropdown_layout2.addWidget(dropdown2)
        # dropdown_layout2.addWidget(checkbox2)
        # dir_mappings_layout.addLayout(dropdown_layout2)

        # # Dropdown 3 with Checkbox
        # dropdown_layout3 = QHBoxLayout()
        # dropdown_label3 = QLabel("Video:", dir_mappings_groupbox)
        # dropdown3 = QComboBox(dir_mappings_groupbox)
        # dropdown3.addItems(["dir1", "dir2", "dir3"])
        # checkbox3 = QCheckBox("Option 3", dir_mappings_groupbox)
        # dropdown_layout3.addWidget(dropdown_label3)
        # dropdown_layout3.addWidget(dropdown3)
        # dropdown_layout3.addWidget(checkbox3)
        # dir_mappings_layout.addLayout(dropdown_layout3)

        # Add the Dir Mappings groupbox to the left layout
        left_layout.addWidget(dir_mappings_groupbox)
        dir_mappings_layout.setSizeConstraint(QLayout.SetMinimumSize)        

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

    def on_radio_button_clicked(self, button):
        print(f"Selected: {button.text()}")

        if 'NTFS' in button.text():            
            self.settings["selected_copy_behaviour"] = "ntfs_junction"
        elif 'Hard Link' in button.text():
             self.settings["selected_copy_behaviour"] = "hard_link"
        else:
            self.settings["selected_copy_behaviour"] = "copy"

    def create_media_mapping_dropdown_menu(self, labels, options, default_indices):
        dropdown_layouts = [] # QHBoxLayout 
        for row, label in enumerate(labels):
            # dropdown_layout = QHBoxLayout()
            dropdown_label = QLabel(label, self.dir_mappings_groupbox)
            dropdown = QComboBox(self.dir_mappings_groupbox)
            dropdown.addItems(options)
            checkbox = QCheckBox("Select", self.dir_mappings_groupbox)
            checkbox.setChecked(True)

            # Set the default index for the dropdown
            default_index = default_indices[row]
            dropdown.setCurrentIndex(default_index)

            self.dir_mappings_layout.addWidget(dropdown_label, row, 0)
            self.dir_mappings_layout.addWidget(dropdown, row, 1)
            self.dir_mappings_layout.addWidget(checkbox, row, 2)     

            self.media_dir_mapping_dropdown_widgets.append( (row, dropdown_label, checkbox, dropdown) )

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
        # out_pupgames_dir = self.settings["output_dir"]
        out_pupgames_dir = self.out_folder_chosen_textfield.text()

        tuples = []

        for platform_xml in self.settings["selected_platform_xml"]:
            platform_name = os.path.splitext(platform_xml)[0] # get the platform name

            src_folder_paths = [] # list of Images\ folder in LB
            dest_folder_paths = []  # list of folder in POPMedia

            for row, dropdown_label, checkbox, dropdown in self.media_dir_mapping_dropdown_widgets:
                if checkbox.isChecked():
                    # check if the selected value in dropdown is empty
                    if len(dropdown.currentText()) > 0:

                        # e.g. src_folder_path value: C:\Programs\Launchbox\Images\SNES\Claer Logo
                        if 'Video Snaps' in dropdown.currentText():
                            src_folder_paths.append(os.path.join(self.settings["lb_folder_dir"], LB_VIDEOS_DATA_PATH, platform_name))
                        elif 'Video Theme' in dropdown.currentText():
                            src_folder_paths.append(os.path.join(self.settings["lb_folder_dir"], LB_VIDEOS_DATA_PATH, platform_name, "Theme"))
                        elif 'Video Marquee' in dropdown.currentText():
                            src_folder_paths.append(os.path.join(self.settings["lb_folder_dir"], LB_VIDEOS_DATA_PATH, platform_name, "Marquee"))
                        else:
                            src_folder_paths.append(os.path.join(self.settings["lb_folder_dir"], LB_IMAGES_DATA_PATH, platform_name, dropdown.currentText()))

                        dest_folder_paths.append(os.path.join(self.settings["output_dir"], platform_name, dropdown_label.text()))
                        pass
                    else:
                        print("Skipped because the selection is empty!")
                else:
                    print("Not processing dir because it is not checked")

            tuples.append( (platform_name, src_folder_paths, dest_folder_paths) )


        self.convert_thread = ConvertThread()
        self.convert_thread.resultReady.connect(self.update_table_view_with_fuzzy_match)
        self.convert_thread.progressUpdated.connect(self.update_progress_bar)
        self.convert_thread.fileProcessed.connect(self.update_status_label)

        self.convert_thread.setData(tuples, self.settings["selected_copy_behaviour"])
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