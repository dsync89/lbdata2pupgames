import json
import xmltodict
import os
import re

# Specify the path to your JSON file
JSON_FILE_PATH = 'MAME_Games_Export_Full.pupgames'
XML_FILE_PATH = 'snes.xml'

def convert_xml_to_json(xml_string):
    # Parse XML to OrderedDict
    xml_dict = xmltodict.parse(xml_string)

    # Convert OrderedDict to JSON
    json_data = json.dumps(xml_dict, indent=2)

    return json_data

def parse_and_pretty_print_json(json_file_path):
    # Read the JSON file
    with open(json_file_path, 'r') as file:
        # Load the JSON data
        data = json.load(file)

    # Pretty print the JSON data
    pretty_json = json.dumps(data, indent=2)

    # Print the pretty printed JSON
    print(pretty_json)

def pretty_print_first_game(json_file_path):
    # Read the JSON file
    with open(json_file_path, 'r') as file:
        # Load the JSON data
        data = json.load(file)

    # Check if the "GameExport" key exists and if it's a non-empty list
    if "GameExport" in data and isinstance(data["GameExport"], list) and data["GameExport"]:
        # Extract the first game object from the array
        first_game = data["GameExport"][0]

        # Pretty print the first game object
        pretty_first_game = json.dumps(first_game, indent=2)

        # Print the pretty printed first game object
        print(pretty_first_game)
    else:
        print("Invalid JSON structure or empty GameExport array.")


def map_fields(game, index):
    # Extracting the filename using regex
    match = re.search(r'\\([^\\]+)$', game["ApplicationPath"])
    gameFileName = match.group(1) if match else ""

    # Helper function to get the value or an empty string if it's None
    def get_value(key):
        return game.get(key, "")

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
        "MediaSearch": "",
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

def convert_xml_to_json(xml_string):
    xml_dict = xmltodict.parse(xml_string)
    games = xml_dict["LaunchBox"]["Game"]
    
    game_export = []
    for i, game in enumerate(games, start=0):
        game_export.append(map_fields(game, i))

    return {"GameExport": game_export}

def replace_null_with_empty(obj):
    if isinstance(obj, list):
        return [replace_null_with_empty(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: replace_null_with_empty(value) for key, value in obj.items()}
    else:
        return "" if obj is None else obj

if __name__ == "__main__":
    # Specify the path to your JSON file
    json_file_path = JSON_FILE_PATH
    xml_file_path = XML_FILE_PATH

    with open(xml_file_path, 'r', encoding='utf-8') as file:
        xml_content = file.read()

    json_result = convert_xml_to_json(xml_content)      

    # Process the entire dictionary
    processed_dict = replace_null_with_empty(json_result)

    # Save JSON to a file
    out_json_filename = f"{os.path.splitext(os.path.basename(xml_file_path))[0]}.pupgames"
    with open(f'{out_json_filename}', 'w') as outfile:
        json.dump(processed_dict, outfile, indent=2)

    print(f"JSON saved to {out_json_filename}")      

    # Convert XML to JSON
    # json_result = convert_xml_to_json(xml_content)

    # # Print the result
    # print(json_result)    

    # Call the main function
    # parse_and_pretty_print_json(json_file_path)

    # pretty_print_first_game(json_file_path)