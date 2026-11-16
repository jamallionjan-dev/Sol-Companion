-- SolSecretLoadoutData.lua - Jamal's secret loadout, shipped with the mod (media/lua/shared). Same "k=v" lines as Sol_SecretLoadout.txt.
-- Empty: SolSecretLoadout captures it once, silently, the next time he carries two firearms, and writes Sol_SecretLoadout.txt;
-- fold_secret_loadout.py then folds that file in here. Not per save, not per life: her death never touches it.
SolSecretLoadoutData = {
    lines = {
    },
}
return SolSecretLoadoutData
