import hashlib, json, os, sys, zipfile, time
FILES = ['build_save.py','lua_patch.py','menu_lua.py','counter_lua.py','turn_lua.py','scenario_lua.py','scenario_names.py','mat_config.py','build_catalog.py','catalog.json','folder_survey.py','dump_object.py',
         'build_reference.py','build_scenarios.py','pdf_extract.py','make_player_mat.py','make_mat_skins.py','build_icons.py','icon_review.py',
         'keyword_pages.py','grid_mat.py','assets_in_survey.py','icon_fixes.json','keyword_fixes.json','scenarios.json','expansion_names.json',
         'build_villains_set.py','villains_set.py','villains_set_spec.json','played_lua.py','card_values.json']
man = {'version': time.strftime('%Y-%m-%d'), 'files': {}}
for f in FILES:
    b = open(f, 'rb').read()
    man['files'][f] = {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
json.dump(man, open('manifest.json', 'w'), indent=1)
out = sys.argv[1]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in FILES + ['install.py', 'manifest.json']: z.write(f)
print(out, os.path.getsize(out), len(FILES) + 2, 'files')
