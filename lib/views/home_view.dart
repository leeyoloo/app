import 'package:flutter/material.dart';
import 'package:miuix_notes_todo/views/todo_view.dart';
import 'package:miuix_notes_todo/views/notes_view.dart';
import 'package:miuix_notes_todo/views/memos_view.dart';
import 'package:miuix_notes_todo/views/diary_view.dart';

class HomeView extends StatefulWidget {
  const HomeView({super.key});

  @override
  State<HomeView> createState() => _HomeViewState();
}

class _HomeViewState extends State<HomeView> {
  int _currentIndex = 0;

  final List<Widget> _pages = const [
    TodoView(),
    NotesView(),
    MemosView(),
    DiaryView(),
  ];

  final List<String> _titles = [
    '待办',
    '笔记',
    '便签',
    '日记',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_currentIndex]),
        centerTitle: true,
      ),
      body: _pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.check_circle_outline),
            label: '待办',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.notes_outlined),
            label: '笔记',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.edit_note_outlined),
            label: '便签',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.book_outlined),
            label: '日记',
          ),
        ],
      ),
    );
  }
}