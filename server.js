require('dotenv').config();
const express = require('express');
const session = require('express-session');
const flash = require('connect-flash');
const bodyParser = require('body-parser');
const { PrismaClient } = require('@prisma/client');

const app = express();
const prisma = new PrismaClient();

// View engine setup
app.set('view engine', 'ejs');
app.use(express.static('public'));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

// Session setup
app.use(session({
  secret: process.env.SESSION_SECRET || 'dev-secret-key',
  resave: false,
  saveUninitialized: false
}));
app.use(flash());

// Make user available in all templates
app.use((req, res, next) => {
  res.locals.user = req.session.user;
  res.locals.messages = req.flash();
  next();
});

// Auth middleware
const requireLogin = (req, res, next) => {
  if (!req.session.user) {
    return res.redirect('/login');
  }
  next();
};

// Routes
app.get('/login', (req, res) => {
  res.render('login');
});

app.post('/login', async (req, res) => {
  try {
    const user = await prisma.user.findUnique({
      where: { username: req.body.username }
    });
    
    if (user && await bcrypt.compare(req.body.password, user.passwordHash)) {
      req.session.user = { id: user.id, username: user.username, isAdmin: user.isAdmin };
      res.redirect('/');
    } else {
      req.flash('error', 'Invalid username or password');
      res.redirect('/login');
    }
  } catch (error) {
    console.error('Login error:', error);
    req.flash('error', 'An error occurred during login');
    res.redirect('/login');
  }
});

app.get('/', requireLogin, async (req, res) => {
  try {
    const articles = await prisma.article.findMany({
      where: { userId: req.session.user.id },
      orderBy: { createdAt: 'desc' }
    });
    res.render('dashboard', { articles });
  } catch (error) {
    console.error('Dashboard error:', error);
    req.flash('error', 'Failed to load articles');
    res.redirect('/login');
  }
});

// Start server
const PORT = process.env.PORT || 5000;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT}`);
});
