@echo off
git add .
echo.
echo.
echo add is done , !
color a
set /p input= Type Commit Here :
git commit -m "%input%"
echo.
echo.
echo commit is Done ! 
echo.
echo.
git push origin main --force
echo.
echo.
echo push is Done ! 
pause