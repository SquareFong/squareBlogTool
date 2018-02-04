#!/usr/bin/python3
#coding:utf-8
import os
import sys,getopt
import pymysql
import time
import re
import json

mdPath="./markdown"
templatesPath="./Templates"
#博客在VPS中的绝对路径
blogRootPath="/var/www/html"
#你的markdown在github上的项目地址
gitAddress="git@github.com:XXXXXXXXXXXXX"

#分别是mysql的地址，用户名，密码，数据库名称
mysqlAddr="localhost"
mysqlUser="root"
mysqlPass="xxxxxxxx"
mysqlDB="squareBlog"

def publishArticle(Title, Date, Tag, markdownName, outputName):
    PostTemplate=open(os.path.join(templatesPath,'post_single.html'),'r').read()
    inf=open(os.path.join(templatesPath,'Info.html'),'r').read()
    os.system("pandoc -f markdown -t html "+markdownName+" > .temp.html")
    article=open('.temp.html','r').read()
    os.system("rm .temp.html")
    topbar=open(os.path.join(templatesPath,'topbar.html'),'r').read()
    o=open(outputName,'w')
    o.write(PostTemplate.format(inf,Title,Date,Tag,article,topbar))
    o.close()
    
#更新home和Posts界面
def updateHome():
    db=pymysql.connect(mysqlAddr,mysqlUser,mysqlPass,mysqlDB,charset='utf8')
    db.encoding ='utf8'
    cursor=db.cursor();
    cursor.execute("select * from files ORDER BY ctime DESC;")
    results=cursor.fetchall()
    db.close()
    blogPath=os.path.join(blogRootPath,'Posts')
    mainbody=""
    singleTemplate=open(os.path.join(templatesPath,'Home_mainBody.html')).read()
    counter=0
    inf=open(os.path.join(templatesPath,'Info.html'),'r').read()
    for mname,hname,tag,ctime,utime in results:
        temp=open(os.path.join(blogPath,hname),'r').read()
        temp=re.split("<!--replace with you articles-->",temp)[1]
        temp=temp.split("\n",3)[2]
        Date=time.strftime('%Y/%m/%d', time.localtime(ctime))
        link="../Posts/"+hname
        mainbody=mainbody+singleTemplate.format(mname[0:len(mname)-3],temp,Date,tag,link)+"<br/>"+"\n"
        ++counter
        if counter == 10:
            #加载主页模板
            homePage=open(os.path.join(templatesPath,'Home.html')).read()
            #加载顶栏
            topbar=open(os.path.join(templatesPath,'topbar_home.html'),'r').read()
            #输出目录
            homepath=os.path.join(blogRootPath,'index.html')
            o=open(homepath,'w')
            o.write(homePage.format(inf,mainbody,topbar))
            o.close()
    if counter < 10:
        # 加载主页模板
        homePage = open(os.path.join(templatesPath, 'Home.html')).read()
        # 加载顶栏
        topbar = open(os.path.join(templatesPath, 'topbar_home.html'), 'r').read()
        # 输出目录
        homepath = os.path.join(blogRootPath, 'index.html')
        o = open(homepath, 'w')
        o.write(homePage.format(inf, mainbody, topbar))
        o.close()
    postPage=open(os.path.join(templatesPath,'Home.html')).read()
    topbar=open(os.path.join(templatesPath,'topbar_posts.html'),'r').read()
    postPath=os.path.join(blogRootPath,'Posts')
    postPath=os.path.join(postPath,'index.html')
    o=open(postPath,'w')
    o.write(postPage.format(inf,mainbody,topbar))
    o.close()
    

def updateAll():
    os.system("cd "+mdPath+" && git pull")
    os.system("cp -ru "+os.path.join(mdPath,"media")+" " + os.path.join(blogRootPath,"media"))
    db=pymysql.connect(mysqlAddr,mysqlUser,mysqlPass,mysqlDB,charset='utf8')
    db.encoding ='utf8'
    cursor=db.cursor();
    cursor.execute("select * from files;")
    results=cursor.fetchall()
    markdowPath=os.path.join(mdPath,"articles")
    mdFiles=[name for name in os.listdir(markdowPath) if name.endswith('.md')]
    #HTMLFiles=[name for name in os.listdir(os.path.join(blogRootPath,'Posts')) if name.endswith('.html')]
    #数据库中有的，检查是否需要更新
    tags=open(os.path.join(mdPath,'tags.json')).read()
    cats=json.loads(tags)
    for mname,hname,tag,ctime,utime in results:
        tagChange=False
        if mname in cats:
            if cats[mname] != tag:
                print(cats[mname] + ' ' + mname)
                tag=cats[mname]
                tagChange=True
                cursor.execute("update files set Tag=\""+ tag +"\" where mName=\"" + mname + "\"")
        if mname in mdFiles:
            mdFiles.remove(mname)
            lastuptime=os.stat(os.path.join(markdowPath,mname)).st_mtime
            print("tagChange:" + str(tagChange))
            if lastuptime > utime or tagChange:#需要更新的
                Date=time.strftime('%Y/%m/%d', time.localtime(ctime))
                markdownName=os.path.join(markdowPath,mname)
                outputName=os.path.join(blogRootPath,'Posts')
                outputName=os.path.join(outputName,hname)
                publishArticle(mname[0:len(mname)-3], Date, tag, markdownName, outputName)
                cursor.execute("update files set utime="+ str(lastuptime) +" where mName=\"" + mname + "\"")
        else:#数据库有，本地却没有，说明文档删除了
            markdownName=os.path.join(markdowPath,mname)
            os.remove(markdownName)
            outputName=os.path.join(blogRootPath,'Posts')
            outputName=os.path.join(outputName,hname)
            os.remove(outputName)
            cursor.execute("DELETE FROM files WHERE mName=" + mname);
            print("error")
    #mdFiles剩下的，新增文档，添加之
    for mname in mdFiles:
        markdownName=os.path.join(markdowPath,mname)
        creattime=os.stat(markdownName).st_ctime
        lastuptime=os.stat(markdownName).st_mtime
        hname=mname[0:len(mname)-3]+".html"
        outputName=os.path.join(blogRootPath,'Posts')
        outputName=os.path.join(outputName,hname)
        if mname in cats:
            tag=cats[mname]
        else:
            tag="default"
        Date=time.strftime('%Y/%m/%d', time.localtime(creattime))
        publishArticle(mname[0:len(mname)-3], Date, tag, markdownName, outputName)
        print(mname[0:len(mname)-3]+' ' + markdownName + ' '+ outputName)
        ex=str("insert into files VALUES(\"{0}\",\"{1}\",\"{2}\",{3},{4})")
        ex=ex.format(mname,hname,tag,creattime,lastuptime)
        print(ex)
        cursor.execute(ex)
    db.commit()
    db.close()

def initBlogSystem():
    if os.path.exists(blogRootPath):
        os.system("rm -rf " + blogRootPath);
    os.system("cp -r "+os.path.join(templatesPath,"InitBlog") + " " +blogRootPath)
    #init markdown File
    if os.path.exists(mdPath):
        os.system("rm -rf " + mdPath);
    os.system("git clone "+gitAddress+" \""+mdPath+"\"")
    #init mysql
    db=pymysql.connect(mysqlAddr,mysqlUser,mysqlPass,mysqlDB)
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS files")
    sql = "CREATE TABLE files (mName VARCHAR(500), hName VARCHAR(500), Tag VARCHAR(100), ctime DOUBLE, utime DOUBLE)"
    cursor.execute(sql)
    db.close()

def help():
    pass

def main(argv):
    if len(argv) >= 3:
        print("Invalid arguments, one operation a time")
        return 1
    try:
        opts, args=getopt.getopt(argv,"iuhr:",["ifile=","ofile="])
    except getopt.GetoptError:
        print("this is help test")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            help()
        elif opt in ("--root","-r"):
            blogRootPath=arg
        elif opt in ("--update","-u"):
            updateAll()
            updateHome()
        elif opt == '-i':
            initBlogSystem()
    
    
if __name__=='__main__':
    main(sys.argv[1:])
