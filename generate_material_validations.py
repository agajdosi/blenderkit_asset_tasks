# -----------------------------------------------------------------------------------
# generate material validation scene for all uploaded assets
# -------------------------------------------- ---------------------------------------

import json
import os
import tempfile
import threading
import time
import pathlib

from blenderkit_server_utils import download, search, paths, upload, send_to_bg, google_drive

results = []
page_size = 100

MAX_ASSETS = int(os.environ.get('MAX_ASSET_COUNT', '100'))
MATERIAL_VALIDATION_FOLDER_ID = "1CnWzlP1e920rF-Zeoacq1gju9Em8Ii-O"
GOOGLE_SHARED_DRIVE_ID = "0ABpmYJ3IosxhUk9PVA"
def render_material_validation_thread(asset_data, api_key):
  '''
  A thread that:
   1.downloads file
   2.starts an instance of Blender that renders the validation
   3.uploads files that were prepared
   4.patches asset data with a new parameter.

  Parameters
  ----------
  asset_data

  Returns
  -------

  '''

  destination_directory = tempfile.gettempdir()

  upload_id = asset_data['files'][0]['downloadUrl'].split('/')[-2]

  # Check if the asset has already been processed
  author_folder_name = f"{asset_data['author']['firstName']}_{asset_data['author']['lastName']}"
  result_file_name = f"{upload_id}_{asset_data['name']}_{asset_data['author']['firstName']}_{asset_data['author']['lastName']}.jpg"

  drive = google_drive.init_drive()

  author_folder_id = google_drive.ensure_folder_exists(drive, author_folder_name, parent_id=MATERIAL_VALIDATION_FOLDER_ID, drive_id=GOOGLE_SHARED_DRIVE_ID)

  f_exists = google_drive.file_exists(drive, result_file_name, folder_id=author_folder_id)
  if f_exists:
      print('file exists, skipping')
      return

  # Download asset
  file_path = download.download_asset(asset_data, api_key=api_key, directory=destination_directory)

  # find template file
  current_dir = pathlib.Path(__file__).parent.resolve()
  template_file_path = os.path.join(current_dir, 'blend_files', 'material_validator_mix.blend')

  # Send to background to generate resolutions
  tempdir = tempfile.mkdtemp()

  # local file path of rendered image
  result_path = os.path.join(tempdir,
                             f"{asset_data['author']['firstName']}_{asset_data['author']['lastName']}",
                             f"{upload_id}_{asset_data['name']}_{asset_data['author']['firstName']}_{asset_data['author']['lastName']}.jpg")


  # send to background to render
  send_to_bg.send_to_bg(asset_data,
                        asset_file_path=file_path,
                        template_file_path=template_file_path,
                        result_path=result_path,
                        script='material_validation_bg.py',
                        binary_type = 'NEWEST')
  # Upload result
  google_drive.upload_file_to_folder(drive, result_path, folder_id=author_folder_id)
  return



def iterate_assets(filepath, thread_function = None, process_count=12, api_key=''):
  ''' iterate through all assigned assets, check for those which need generation and send them to res gen'''
  assets = search.load_assets_list(filepath)
  threads = []
  for asset_data in assets:
    if asset_data is not None:
      print('downloading and generating resolution for  %s' % asset_data['name'])
      thread = threading.Thread(target=thread_function, args=(asset_data, api_key))
      thread.start()
      threads.append(thread)
      while len(threads) > process_count - 1:
        for t in threads:
          if not t.is_alive():
            threads.remove(t)
          break;
        time.sleep(0.1) # wait for a bit to finish all threads


def main():
  dpath = tempfile.gettempdir()
  filepath = os.path.join(dpath, 'assets_for_resolutions.json')
  params = {
      'order': '-created',
      'asset_type': 'material',
      'verification_status': 'uploaded'
  }
  search.get_search_simple(params, filepath=filepath,  page_size=min(MAX_ASSETS, 100), max_results=MAX_ASSETS,
                           api_key=paths.API_KEY)


  assets = search.load_assets_list(filepath)
  print('ASSETS TO BE PROCESSED')
  for i, a in enumerate(assets):
    print(a['name'], a['assetType'])

  iterate_assets(filepath, process_count=1, api_key=paths.API_KEY, thread_function=render_material_validation_thread)

if __name__ == '__main__':
  main()